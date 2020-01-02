exports.max_num_of_search_results = 12;

function stream_matches_query(stream_name, q) {
    return common.phrase_match(q, stream_name);
}

function make_person_highlighter(query) {
    const hilite = typeahead_helper.make_query_highlighter(query);

    return function (person) {
        if (settings_org.show_email()) {
            return hilite(person.full_name) + " &lt;" + hilite(person.email) + "&gt;";
        }
        return hilite(person.full_name);
    };
}

function match_criteria(operators, criteria) {
    const filter = new Filter(operators);
    return _.any(criteria, function (cr) {
        if (_.has(cr, 'operand')) {
            return filter.has_operand(cr.operator, cr.operand);
        }
        return filter.has_operator(cr.operator);
    });
}

function check_validity(last, operators, valid, invalid) {
    // valid: list of strings valid for the last operator
    // invalid: list of operators invalid for any previous operators except last.
    if (valid.indexOf(last.operator) === -1) {
        return false;
    }
    if (match_criteria(operators, invalid)) {
        return false;
    }
    return true;
}

function format_as_suggestion(terms) {
    return {
        description: Filter.describe(terms),
        search_string: Filter.unparse(terms),
    };
}

function compare_by_huddle(huddle) {
    huddle = _.map(huddle.slice(0, -1), function (person) {
        person = people.get_by_email(person);
        if (person) {
            return person.user_id;
        }
    });

    // Construct dict for all huddles, so we can lookup each's recency
    const huddles = activity.get_huddles();
    const huddle_dict = {};
    for (let i = 0; i < huddles.length; i += 1) {
        huddle_dict[huddles[i]] = i + 1;
    }

    return function (person1, person2) {
        const huddle1 = huddle.concat(person1.user_id).sort().join(',');
        const huddle2 = huddle.concat(person2.user_id).sort().join(',');

        // If not in the dict, assign an arbitrarily high index
        const score1 = huddle_dict[huddle1] || 100;
        const score2 = huddle_dict[huddle2] || 100;
        const diff = score1 - score2;

        if (diff !== 0) {
            return diff;
        }
        return typeahead_helper.compare_by_pms(person1, person2);
    };
}

function get_stream_suggestions(last, operators) {
    const valid = ['stream', 'search', ''];
    const invalid = [
        {operator: 'stream'},
        {operator: 'streams'},
        {operator: 'is', operand: 'private'},
        {operator: 'pm-with'},
    ];
    if (!check_validity(last, operators, valid, invalid)) {
        return [];
    }

    const query = last.operand;
    let streams = stream_data.subscribed_streams();

    streams = _.filter(streams, function (stream) {
        return stream_matches_query(stream, query);
    });

    streams = typeahead_helper.sorter(query, streams);

    const regex = typeahead_helper.build_highlight_regex(query);
    const hilite = typeahead_helper.highlight_with_escaping_and_regex;

    const objs = _.map(streams, function (stream) {
        const prefix = 'stream';
        const highlighted_stream = hilite(regex, stream);
        const verb = last.negated ? 'exclude ' : '';
        const description = verb + prefix + ' ' + highlighted_stream;
        const term = {
            operator: 'stream',
            operand: stream,
            negated: last.negated,
        };
        const search_string = Filter.unparse([term]);
        return {description: description, search_string: search_string};
    });

    return objs;
}

function get_group_suggestions(last, operators) {
    if (!check_validity(last, operators, ['pm-with'], [{operator: 'stream'}])) {
        return [];
    }

    const operand = last.operand;
    const negated = last.negated;

    // The operand has the form "part1,part2,pa", where all but the last part
    // are emails, and the last part is an arbitrary query.
    //
    // We only generate group suggestions when there's more than one part, and
    // we only use the last part to generate suggestions.

    const last_comma_index = operand.lastIndexOf(',');
    if (last_comma_index < 0) {
        return [];
    }

    // Neither all_but_last_part nor last_part include the final comma.
    const all_but_last_part = operand.slice(0, last_comma_index);
    const last_part = operand.slice(last_comma_index + 1);

    // We don't suggest a person if their email is already present in the
    // operand (not including the last part).
    const parts = all_but_last_part.split(',').concat(people.my_current_email());

    const person_matcher = people.build_person_matcher(last_part);
    let persons = people.filter_all_persons(function (person) {
        if (_.contains(parts, person.email)) {
            return false;
        }
        return last_part === '' || person_matcher(person);
    });

    persons.sort(compare_by_huddle(parts));

    // Take top 15 persons, since they're ordered by pm_recipient_count.
    persons = persons.slice(0, 15);

    const prefix = Filter.operator_to_prefix('pm-with', negated);

    const highlight_person = make_person_highlighter(last_part);

    const suggestions = _.map(persons, function (person) {
        const term = {
            operator: 'pm-with',
            operand: all_but_last_part + ',' + person.email,
            negated: negated,
        };
        const name = highlight_person(person);
        const description = prefix + ' ' + Handlebars.Utils.escapeExpression(all_but_last_part) + ',' + name;
        let terms = [term];
        if (negated) {
            terms = [{operator: 'is', operand: 'private'}, term];
        }
        const search_string = Filter.unparse(terms);
        return {description: description, search_string: search_string};
    });

    return suggestions;
}

// Possible args for autocomplete_operator: pm-with, sender, from
function get_person_suggestions(last, operators, autocomplete_operator) {
    if (last.operator === "is" && last.operand === "private") {
        // Interpret 'is:private' as equivalent to 'pm-with:'
        last = {operator: "pm-with", operand: "", negated: false};
    }

    const query = last.operand;

    // Be especially strict about the less common "from" operator.
    if (autocomplete_operator === 'from' && last.operator !== 'from') {
        return [];
    }

    const valid = ['search', autocomplete_operator];
    let invalid;
    if (autocomplete_operator === 'pm-with') {
        invalid = [{operator: 'pm-with'}, {operator: 'stream'}];
    } else {
        // If not pm-with, then this must either be 'sender' or 'from'
        invalid = [{operator: 'sender'}, {operator: 'from'}];
    }

    if (!check_validity(last, operators, valid, invalid)) {
        return [];
    }

    const persons = people.get_people_for_search_bar(query);

    persons.sort(typeahead_helper.compare_by_pms);

    const prefix = Filter.operator_to_prefix(autocomplete_operator, last.negated);

    const highlight_person = make_person_highlighter(query);

    const objs = _.map(persons, function (person) {
        const name = highlight_person(person);
        const description = prefix + ' ' + name;
        const terms = [{
            operator: autocomplete_operator,
            operand: person.email,
            negated: last.negated,
        }];
        if (autocomplete_operator === 'pm-with' && last.negated) {
            // In the special case of '-pm-with', add 'is:private' before it
            // because we assume the user still wants to narrow to PMs
            terms.unshift({operator: 'is', operand: 'private'});
        }
        const search_string = Filter.unparse(terms);
        return {description: description, search_string: search_string};
    });

    return objs;
}

function get_default_suggestion(operators) {
    // Here we return the canonical suggestion for the last query that the
    // user typed.
    if (operators !== undefined && operators.length > 0) {
        return format_as_suggestion(operators);
    }
    return false;
}

function get_default_suggestion_legacy(operators) {
    // Here we return the canonical suggestion for the full query that the
    // user typed.  (The caller passes us the parsed query as "operators".)
    if (operators.length === 0) {
        return {description: '', search_string: ''};
    }
    return format_as_suggestion(operators);
}

function get_topic_suggestions(last, operators) {
    const invalid = [
        {operator: 'pm-with'},
        {operator: 'is', operand: 'private'},
        {operator: 'topic'},
    ];
    if (!check_validity(last, operators, ['stream', 'topic', 'search'], invalid)) {
        return [];
    }

    const operator = Filter.canonicalize_operator(last.operator);
    const operand = last.operand;
    const negated = operator === 'topic' && last.negated;
    let stream;
    let guess;
    const filter = new Filter(operators);
    const suggest_operators = [];

    // stream:Rome -> show all Rome topics
    // stream:Rome topic: -> show all Rome topics
    // stream:Rome f -> show all Rome topics with a word starting in f
    // stream:Rome topic:f -> show all Rome topics with a word starting in f
    // stream:Rome topic:f -> show all Rome topics with a word starting in f

    // When narrowed to a stream:
    //   topic: -> show all topics in current stream
    //   foo -> show all topics in current stream with words starting with foo

    // If somebody explicitly types search:, then we might
    // not want to suggest topics, but I feel this is a very
    // minor issue, and Filter.parse() is currently lossy
    // in terms of telling us whether they provided the operator,
    // i.e. "foo" and "search:foo" both become [{operator: 'search', operand: 'foo'}].
    switch (operator) {
    case 'stream':
        guess = '';
        stream = operand;
        suggest_operators.push(last);
        break;
    case 'topic':
    case 'search':
        guess = operand;
        if (filter.has_operator('stream')) {
            stream = filter.operands('stream')[0];
        } else {
            stream = narrow_state.stream();
            suggest_operators.push({operator: 'stream', operand: stream});
        }
        break;
    }

    if (!stream) {
        return [];
    }


    const stream_id = stream_data.get_stream_id(stream);
    if (!stream_id) {
        return [];
    }

    let topics = topic_data.get_recent_names(stream_id);

    if (!topics || !topics.length) {
        return [];
    }

    // Be defensive here in case stream_data.get_recent_topics gets
    // super huge, but still slice off enough topics to find matches.
    topics = topics.slice(0, 300);

    if (guess !== '') {
        topics = _.filter(topics, function (topic) {
            return common.phrase_match(guess, topic);
        });
    }

    topics = topics.slice(0, 10);

    // Just use alphabetical order.  While recency and read/unreadness of
    // topics do matter in some contexts, you can get that from the left sidebar,
    // and I'm leaning toward high scannability for autocompletion.  I also don't
    // care about case.
    topics.sort();

    return _.map(topics, function (topic) {
        const topic_term = {operator: 'topic', operand: topic, negated: negated};
        const operators = suggest_operators.concat([topic_term]);
        return format_as_suggestion(operators);
    });
}

function get_operator_subset_suggestions(operators) {
    // For stream:a topic:b search:c, suggest:
    //  stream:a topic:b
    //  stream:a
    if (operators.length < 1) {
        return [];
    }

    let i;
    const suggestions = [];

    for (i = operators.length - 1; i >= 1; i -= 1) {
        const subset = operators.slice(0, i);
        suggestions.push(format_as_suggestion(subset));
    }

    return suggestions;
}

function get_special_filter_suggestions(last, operators, suggestions) {
    const is_search_operand_negated = last.operator === 'search' && last.operand[0] === '-';
    // Negating suggestions on is_search_operand_negated is required for
    // suggesting negated operators.
    if (last.negated || is_search_operand_negated) {
        suggestions = _.map(suggestions, function (suggestion) {
            return {
                search_string: '-' + suggestion.search_string,
                description: 'exclude ' + suggestion.description,
                invalid: suggestion.invalid,
            };
        });
    }

    const last_string = Filter.unparse([last]).toLowerCase();
    suggestions = _.filter(suggestions, function (s) {
        if (match_criteria(operators, s.invalid)) {
            return false;
        }
        if (last_string === '') {
            return true;
        }

        // returns the substring after the ":" symbol.
        const suggestion_operand = s.search_string.substring(s.search_string.indexOf(":") + 1);
        // e.g for `att` search query, `has:attachment` should be suggested.
        const show_operator_suggestions = last.operator === 'search' && suggestion_operand.toLowerCase().indexOf(last_string) === 0;
        return s.search_string.toLowerCase().indexOf(last_string) === 0 ||
               show_operator_suggestions ||
               s.description.toLowerCase().indexOf(last_string) === 0;
    });

    // Only show home if there's an empty bar
    if (operators.length === 0 && last_string === '') {
        suggestions.unshift({search_string: '', description: 'All messages'});
    }
    return suggestions;
}

function get_streams_filter_suggestions(last, operators) {
    const suggestions = [
        {
            search_string: 'streams:public',
            description: 'All public streams in organization',
            invalid: [
                {operator: 'is', operand: 'private'},
                {operator: 'stream'},
                {operator: 'group-pm-with'},
                {operator: 'pm-with'},
                {operator: 'in'},
                {operator: 'streams'},
            ],

        },
    ];
    return get_special_filter_suggestions(last, operators, suggestions);
}
function get_is_filter_suggestions(last, operators) {
    const suggestions = [
        {
            search_string: 'is:private',
            description: 'private messages',
            invalid: [
                {operator: 'is', operand: 'private'},
                {operator: 'stream'},
                {operator: 'pm-with'},
                {operator: 'in'},
            ],

        },
        {
            search_string: 'is:starred',
            description: 'starred messages',
            invalid: [
                {operator: 'is', operand: 'starred'},
            ],
        },
        {
            search_string: 'is:mentioned',
            description: '@-mentions',
            invalid: [
                {operator: 'is', operand: 'mentioned'},
            ],
        },
        {
            search_string: 'is:alerted',
            description: 'alerted messages',
            invalid: [
                {operator: 'is', operand: 'alerted'},
            ],
        },
        {
            search_string: 'is:unread',
            description: 'unread messages',
            invalid: [
                {operator: 'is', operand: 'unread'},
            ],
        },
    ];
    return get_special_filter_suggestions(last, operators, suggestions);
}

function get_has_filter_suggestions(last, operators) {
    const suggestions = [
        {
            search_string: 'has:link',
            description: 'messages with one or more link',
            invalid: [
                {operator: 'has', operand: 'link'},
            ],
        },
        {
            search_string: 'has:image',
            description: 'messages with one or more image',
            invalid: [
                {operator: 'has', operand: 'image'},
            ],
        },
        {
            search_string: 'has:attachment',
            description: 'messages with one or more attachment',
            invalid: [
                {operator: 'has', operand: 'attachment'},
            ],
        },
    ];
    return get_special_filter_suggestions(last, operators, suggestions);
}


function get_sent_by_me_suggestions(last, operators) {
    const last_string = Filter.unparse([last]).toLowerCase();
    const negated = last.negated || last.operator === 'search' && last.operand[0] === '-';
    const negated_symbol = negated ? '-' : '';
    const verb = negated ? 'exclude ' : '';

    const sender_query = negated_symbol + 'sender:' + people.my_current_email();
    const from_query = negated_symbol + 'from:' + people.my_current_email();
    const sender_me_query = negated_symbol + 'sender:me';
    const from_me_query = negated_symbol + 'from:me';
    const sent_string = negated_symbol + 'sent';
    const description = verb + 'sent by me';

    const invalid = [
        {operator: 'sender'},
        {operator: 'from'},
    ];

    if (match_criteria(operators, invalid)) {
        return [];
    }

    if (last.operator === '' || sender_query.indexOf(last_string) === 0 ||
        sender_me_query.indexOf(last_string) === 0 || last_string === sent_string) {
        return [
            {
                search_string: sender_query,
                description: description,
            },
        ];
    } else if (from_query.indexOf(last_string) === 0 || from_me_query.indexOf(last_string) === 0) {
        return [
            {
                search_string: from_query,
                description: description,
            },
        ];
    }
    return [];
}

function get_operator_suggestions(last) {
    if (!(last.operator === 'search')) {
        return [];
    }
    let last_operand = last.operand;

    let negated = false;
    if (last_operand.indexOf("-") === 0) {
        negated = true;
        last_operand = last_operand.slice(1);
    }

    let choices = ['stream', 'topic', 'pm-with', 'sender', 'near', 'from', 'group-pm-with'];
    choices = _.filter(choices, function (choice) {
        return common.phrase_match(last_operand, choice);
    });

    return _.map(choices, function (choice) {
        const op = [{operator: choice, operand: '', negated: negated}];
        return format_as_suggestion(op);
    });
}

function make_attacher(base) {
    const self = {};
    self.result = [];
    const prev = {};

    function prepend_base(suggestion) {
        if (base && base.description.length > 0) {
            suggestion.search_string = base.search_string + " " + suggestion.search_string;
            suggestion.description = base.description + ", " + suggestion.description;
        }
    }

    self.push = function (suggestion) {
        if (!prev[suggestion.search_string]) {
            prev[suggestion.search_string] = suggestion;
            self.result.push(suggestion);
        }
    };

    self.concat = function (suggestions) {
        _.each(suggestions, self.push);
    };

    self.attach_many = function (suggestions) {
        _.each(suggestions, function (suggestion) {
            prepend_base(suggestion);
            self.push(suggestion);
        });
    };

    return self;
}

exports.get_search_result = function (base_query, query) {
    let suggestion;
    let suggestions;

    // base_query_operators correspond to the existing pills. query_operators correspond
    // to the operators for the query in the input. This query may contain one or more
    // operators. e.g if `is:starred stream:Ver` was typed without selecting the typeahead
    // or pressing enter in between i.e search pill for is:starred has not yet been added,
    // then `base` should be equal to the default suggestion for `is:starred`. Thus the
    // description of `is:starred` will act as a prefix in every suggestion.
    const base_query_operators = Filter.parse(base_query);
    const query_operators = Filter.parse(query);
    const operators = base_query_operators.concat(query_operators);
    let last = {operator: '', operand: '', negated: false};
    if (query_operators.length > 0) {
        last = query_operators.slice(-1)[0];
    } else {
        // If query_operators = [] then last will remain
        // {operator: '', operand: '', negated: false}; from above.
        // `last` has not yet been added to operators/query_operators.
        // The code below adds last to operators/query_operators
        operators.push(last);
        query_operators.push(last);
    }

    const person_suggestion_ops = ['sender', 'pm-with', 'from', 'group-pm'];
    const operators_len = operators.length;
    const query_operators_len = query_operators.length;

    // Handle spaces in person name in new suggestions only. Checks if the last operator is
    // 'search' and the second last operator in query_operators is one out of person_suggestion_ops.
    // e.g for `sender:Ted sm`, initially last = {operator: 'search', operand: 'sm'....}
    // and second last is {operator: 'sender', operand: 'sm'....}. If the second last operand
    // is an email of a user, both of these operators remain unchanged. Otherwise search operator
    // will be deleted and new last will become {operator:'sender', operand: 'Ted sm`....}.
    if (query_operators_len > 1 &&
        last.operator === 'search' &&
        person_suggestion_ops.indexOf(query_operators[query_operators_len - 2].operator) !== -1) {
        const person_op = query_operators[query_operators_len - 2];
        if (!people.reply_to_to_user_ids_string(person_op.operand)) {
            last = {
                operator: person_op.operator,
                operand: person_op.operand + ' ' + last.operand,
                negated: person_op.negated,
            };
            operators[operators_len - 2] = last;
            operators.splice(-1, 1);
            query_operators[query_operators_len - 2] = last;
            query_operators.splice(-1, 1);
        }
    }

    const base = get_default_suggestion(query_operators.slice(0, -1));
    const attacher = make_attacher(base);
    const attach = attacher.attach_many;

    // Display the default first
    // `has` and `is` operators work only on predefined categories. Default suggestion
    // is not displayed in that case. e.g. `messages with one or more abc` as
    // a suggestion for `has:abc`does not make sense.
    if (last.operator !== '' && last.operator !== 'has' && last.operator !== 'is') {
        suggestion = get_default_suggestion(query_operators);
        if (suggestion) {
            attacher.push(suggestion);
        }
    }

    let base_operators = [];
    if (operators.length > 1) {
        base_operators = operators.slice(0, -1);
    }

    suggestions = get_streams_filter_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_is_filter_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_sent_by_me_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_stream_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_person_suggestions(last, base_operators, 'sender');
    attach(suggestions);

    suggestions = get_person_suggestions(last, base_operators, 'pm-with');
    attach(suggestions);

    suggestions = get_person_suggestions(last, base_operators, 'from');
    attach(suggestions);

    suggestions = get_person_suggestions(last, base_operators, 'group-pm-with');
    attach(suggestions);

    suggestions = get_group_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_topic_suggestions(last, base_operators);
    attach(suggestions);

    suggestions = get_operator_suggestions(last);
    attach(suggestions);

    suggestions = get_has_filter_suggestions(last, base_operators);
    attach(suggestions);

    attacher.concat(suggestions);
    return attacher.result;
};

exports.get_search_result_legacy = function (query) {
    let suggestion;

    // Add an entry for narrow by operators.
    const operators = Filter.parse(query);
    let last = {operator: '', operand: '', negated: false};
    if (operators.length > 0) {
        last = operators.slice(-1)[0];
    }

    const person_suggestion_ops = ['sender', 'pm-with', 'from', 'group-pm'];
    const operators_len = operators.length;

    // Handle spaces in person name in new suggestions only. Checks if the last operator is
    // 'search' and the second last operator is one out of person_suggestion_ops.
    // e.g for `sender:Ted sm`, initially last = {operator: 'search', operand: 'sm'....}
    // and second last is {operator: 'sender', operand: 'sm'....}. If the second last operand
    // is an email of a user, both of these operators remain unchanged. Otherwise search operator
    // will be deleted and new last will become {operator:'sender', operand: 'Ted sm`....}.
    if (operators_len > 1 &&
        last.operator === 'search' &&
        person_suggestion_ops.indexOf(operators[operators_len - 2].operator) !== -1) {
        const person_op = operators[operators_len - 2];
        if (!people.reply_to_to_user_ids_string(person_op.operand)) {
            last = {
                operator: person_op.operator,
                operand: person_op.operand + ' ' + last.operand,
                negated: person_op.negated,
            };
            operators[operators_len - 2] = last;
            operators.splice(-1, 1);
        }
    }

    let base_operators = [];
    if (operators.length > 1) {
        base_operators = operators.slice(0, -1);
    }
    const base = get_default_suggestion_legacy(base_operators);
    const attacher = make_attacher(base);

    // Display the default first
    // `has` and `is` operators work only on predefined categories. Default suggestion
    // is not displayed in that case. e.g. `messages with one or more abc` as
    // a suggestion for `has:abc`does not make sense.
    if (last.operator !== '' && last.operator !== 'has' && last.operator !== 'is') {
        suggestion = get_default_suggestion_legacy(operators);
        attacher.push(suggestion);
    }

    function get_people(flavor) {
        return function (last, base_operators) {
            return get_person_suggestions(last, base_operators, flavor);
        };
    }

    const filterers = [
        get_streams_filter_suggestions,
        get_is_filter_suggestions,
        get_sent_by_me_suggestions,
        get_stream_suggestions,
        get_people('sender'),
        get_people('pm-with'),
        get_people('from'),
        get_people('group-pm-with'),
        get_group_suggestions,
        get_topic_suggestions,
        get_operator_suggestions,
        get_has_filter_suggestions,
    ];

    const max_items = exports.max_num_of_search_results;

    _.each(filterers, function (filterer) {
        if (attacher.result.length < max_items) {
            const suggestions = filterer(last, base_operators);
            attacher.attach_many(suggestions);
        }
    });

    if (attacher.result.length < max_items) {
        const subset_suggestions = get_operator_subset_suggestions(operators);
        attacher.concat(subset_suggestions);
    }

    return attacher.result.slice(0, max_items);
};

exports.get_suggestions_legacy = function (query) {
    const result = exports.get_search_result_legacy(query);
    return exports.finalize_search_result(result);
};

exports.get_suggestions = function (base_query, query) {
    const result = exports.get_search_result(base_query, query);
    return exports.finalize_search_result(result);
};

exports.finalize_search_result = function (result) {
    _.each(result, function (sug) {
        const first = sug.description.charAt(0).toUpperCase();
        sug.description = first + sug.description.slice(1);
    });

    // Typeahead expects us to give it strings, not objects,
    // so we maintain our own hash back to our objects
    const lookup_table = {};
    _.each(result, function (obj) {
        lookup_table[obj.search_string] = obj;
    });
    const strings = _.map(result, function (obj) {
        return obj.search_string;
    });
    return {
        strings: strings,
        lookup_table: lookup_table,
    };
};

window.search_suggestion = exports;
