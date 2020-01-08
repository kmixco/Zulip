const render_typeahead_list_item = require('../templates/typeahead_list_item.hbs');
const Dict = require('./dict').Dict;

// Returns an array of private message recipients, removing empty elements.
// For example, "a,,b, " => ["a", "b"]
exports.get_cleaned_pm_recipients = function (query_string) {
    let recipients = util.extract_pm_recipients(query_string);
    recipients = _.filter(recipients, function (elem) {
        return elem.match(/\S/);
    });
    return recipients;
};

exports.build_highlight_regex = function (query) {
    // the regex below is based on bootstrap code
    query = query.replace(/[\-\[\]{}()*+?.,\\\^$|#\s]/g, '\\$&');
    const regex = new RegExp('(' + query + ')', 'ig');
    return regex;
};

exports.highlight_with_escaping_and_regex = function (regex, item) {
    // We need to assemble this manually (as opposed to doing 'join') because we need to
    // (1) escape all the pieces and (2) the regex is case-insensitive, and we need
    // to know the case of the content we're replacing (you can't just use a bolded
    // version of 'query')

    const pieces = item.split(regex);
    let result = "";
    _.each(pieces, function (piece) {
        if (piece.match(regex)) {
            result += "<strong>" + Handlebars.Utils.escapeExpression(piece) + "</strong>";
        } else {
            result += Handlebars.Utils.escapeExpression(piece);
        }
    });
    return result;
};

exports.make_query_highlighter = function (query) {
    let i;
    query = query.toLowerCase();

    const regex = exports.build_highlight_regex(query);

    return function (phrase) {
        let result = "";
        const parts = phrase.split(' ');
        for (i = 0; i < parts.length; i += 1) {
            if (i > 0) {
                result += " ";
            }
            result += exports.highlight_with_escaping_and_regex(regex, parts[i]);
        }
        return result;
    };
};

exports.render_typeahead_item = function (args) {
    args.has_image = args.img_src !== undefined;
    args.has_secondary = args.secondary !== undefined;
    return render_typeahead_list_item(args);
};

const rendered = { persons: new Dict(), streams: new Dict(), user_groups: new Dict() };

exports.render_person = function (person) {
    if (person.special_item_text) {
        return exports.render_typeahead_item({
            primary: person.special_item_text,
            is_person: true,
        });
    }

    let html = rendered.persons.get(person.user_id);
    if (html === undefined) {
        const avatar_url = people.small_avatar_url_for_person(person);

        const typeahead_arguments = {
            primary: person.full_name,
            img_src: avatar_url,
            is_person: true,
        };
        if (settings_org.show_email()) {
            typeahead_arguments.secondary = person.email;
        }
        html = exports.render_typeahead_item(typeahead_arguments);
        rendered.persons.set(person.user_id, html);
    }
    return html;
};

exports.clear_rendered_person = function (user_id) {
    rendered.persons.del(user_id);
};

exports.render_user_group = function (user_group) {
    let html = rendered.user_groups.get(user_group.id);
    if (html === undefined) {
        html = exports.render_typeahead_item({
            primary: user_group.name,
            secondary: user_group.description,
            is_user_group: true,
        });
        rendered.user_groups.set(user_group.id, html);
    }

    return html;
};

exports.render_person_or_user_group = function (item) {
    if (user_groups.is_user_group(item)) {
        return exports.render_user_group(item);
    }

    return exports.render_person(item);
};

exports.clear_rendered_stream = function (stream_id) {
    if (rendered.streams.has(stream_id)) {
        rendered.streams.del(stream_id);
    }
};

exports.render_stream = function (stream) {
    let desc = stream.description;
    const short_desc = desc.substring(0, 35);

    if (desc !== short_desc) {
        desc = short_desc + "...";
    }

    let html = rendered.streams.get(stream.stream_id);
    if (html === undefined) {
        html = exports.render_typeahead_item({
            primary: stream.name,
            secondary: desc,
            is_unsubscribed: !stream.subscribed,
        });
        rendered.streams.set(stream.stream_id, html);
    }

    return html;
};

exports.render_emoji = function (item) {
    const args = {
        is_emoji: true,
        primary: item.emoji_name.split("_").join(" "),
    };
    if (emoji.active_realm_emojis.hasOwnProperty(item.emoji_name)) {
        args.img_src = item.emoji_url;
    } else {
        args.emoji_code = item.emoji_code;
    }
    return exports.render_typeahead_item(args);
};

// manipulate prefix_sort to select popular emojis first
// This is kinda a hack and so probably not our long-term solution.
function emoji_prefix_sort(query, objs, get_item) {
    const prefix_sort = util.prefix_sort(query, objs, get_item);
    const popular_emoji_matches = [];
    const other_emoji_matches = [];
    prefix_sort.matches.forEach(function (obj) {
        if (emoji.frequently_used_emojis_list.indexOf(obj.emoji_code) !== -1) {
            popular_emoji_matches.push(obj);
        } else {
            other_emoji_matches.push(obj);
        }
    });
    return { matches: popular_emoji_matches.concat(other_emoji_matches), rest: prefix_sort.rest };
}

exports.sorter = function (query, objs, get_item) {
    const results = util.prefix_sort(query, objs, get_item);
    return results.matches.concat(results.rest);
};

exports.compare_by_pms = function (user_a, user_b) {
    const count_a = people.get_recipient_count(user_a);
    const count_b = people.get_recipient_count(user_b);

    if (count_a > count_b) {
        return -1;
    } else if (count_a < count_b) {
        return 1;
    }

    if (!user_a.is_bot && user_b.is_bot) {
        return -1;
    } else if (user_a.is_bot && !user_b.is_bot) {
        return 1;
    }

    // We use alpha sort as a tiebreaker, which might be helpful for
    // new users.
    if (user_a.full_name < user_b.full_name) {
        return -1;
    } else if (user_a === user_b) {
        return 0;
    }
    return 1;
};

exports.compare_people_for_relevance = function (
    person_a,
    person_b,
    tertiary_compare,
    current_stream) {

    // give preference to "all", "everyone" or "stream"
    // We use is_broadcast for a quick check.  It will
    // true for all/everyone/stream and undefined (falsy)
    // for actual people.
    if (person_a.is_broadcast) {
        if (person_b.is_broadcast) {
            return person_a.idx - person_b.idx;
        }
        return -1;
    } else if (person_b.is_broadcast) {
        return 1;
    }

    // Now handle actual people users.

    // give preference to subscribed users first
    if (current_stream !== undefined) {
        const a_is_sub = stream_data.is_user_subscribed(current_stream, person_a.user_id);
        const b_is_sub = stream_data.is_user_subscribed(current_stream, person_b.user_id);

        if (a_is_sub && !b_is_sub) {
            return -1;
        } else if (!a_is_sub && b_is_sub) {
            return 1;
        }
    }

    // give preference to pm partners if both (are)/(are not) subscribers
    const a_is_partner = pm_conversations.is_partner(person_a.user_id);
    const b_is_partner = pm_conversations.is_partner(person_b.user_id);

    if (a_is_partner && !b_is_partner) {
        return -1;
    } else if (!a_is_partner && b_is_partner) {
        return 1;
    }

    return tertiary_compare(person_a, person_b);
};

exports.sort_people_for_relevance = function (objs, current_stream_name, current_topic) {
    // If sorting for recipientbox typeahead or compose state is private, then current_stream = ""
    let current_stream = false;
    if (current_stream_name) {
        current_stream = stream_data.get_sub(current_stream_name);
    }
    if (!current_stream) {
        objs.sort(function (person_a, person_b) {
            return exports.compare_people_for_relevance(
                person_a,
                person_b,
                exports.compare_by_pms
            );
        });
    } else {
        const stream_id = current_stream.stream_id;

        objs.sort(function (person_a, person_b) {
            return exports.compare_people_for_relevance(
                person_a,
                person_b,
                function (user_a, user_b) {
                    return recent_senders.compare_by_recency(
                        user_a,
                        user_b,
                        stream_id,
                        current_topic
                    );
                },
                current_stream.name
            );
        });
    }

    return objs;
};

exports.compare_by_popularity = function (lang_a, lang_b) {
    const diff = pygments_data.langs[lang_b] - pygments_data.langs[lang_a];
    if (diff !== 0) {
        return diff;
    }
    return util.strcmp(lang_a, lang_b);
};

exports.sort_languages = function (matches, query) {
    const results = util.prefix_sort(query, matches, function (x) { return x; });

    // Languages that start with the query
    results.matches = results.matches.sort(exports.compare_by_popularity);

    // Push exact matches to top.
    const match_index = results.matches.indexOf(query);
    if (match_index > -1) {
        results.matches.splice(match_index, 1);
        results.matches.unshift(query);
    }

    // Languages that have the query somewhere in their name
    results.rest = results.rest.sort(exports.compare_by_popularity);
    return results.matches.concat(results.rest);
};

exports.sort_recipients = function (users, query, current_stream, current_topic, groups) {
    function sort_relevance(items) {
        return exports.sort_people_for_relevance(
            items, current_stream, current_topic);
    }

    function partition(items, get_item) {
        /*
            The name for util.prefix_sort is quite
            misleading.  It really just partitions a list
            of items into two groups--good and bad.  But
            for the goods, it puts case-senstitive matches
            before case-insensitive matches, otherwise preserving
            the original sort, so it's kinda like a sort
            if you're starting with data that's most sorted
            the way you want it.  And then we re-sort it, but
            maybe sort_people_for_relevance is a stable sort?
            And do we actually care whether matches are case
            sensitive here?  I don't know.
        */

        return util.prefix_sort(query, items, get_item);
    }

    const users_name_results = partition(
        users,
        (p) => p.full_name);

    const email_results = partition(
        users_name_results.rest,
        (p) => p.email);

    let result = sort_relevance(users_name_results.matches);

    let groups_results;
    if (groups !== undefined) {
        groups_results = partition(
            groups,
            (g) => g.name);
        result = result.concat(groups_results.matches);
    }

    result = result.concat(sort_relevance(email_results.matches));

    let rest_sorted = sort_relevance(email_results.rest);
    if (groups !== undefined) {
        rest_sorted = rest_sorted.concat(groups_results.rest);
    }
    return result.concat(rest_sorted);
};

function slash_command_comparator(slash_command_a, slash_command_b) {
    if (slash_command_a.name < slash_command_b.name) {
        return -1;
    } else if (slash_command_a.name > slash_command_b.name) {
        return 1;
    }
}
exports.sort_slash_commands = function (matches, query) {
    // We will likely want to in the future make this sort the
    // just-`/` commands by something approximating usefulness.
    const results = util.prefix_sort(query, matches, function (x) { return x.name; });
    results.matches = results.matches.sort(slash_command_comparator);
    results.rest = results.rest.sort(slash_command_comparator);
    return results.matches.concat(results.rest);
};

exports.sort_emojis = function (matches, query) {
    // TODO: sort by category in v2
    const results = emoji_prefix_sort(query, matches, function (x) { return x.emoji_name; });
    return results.matches.concat(results.rest);
};

// Gives stream a score from 0 to 3 based on its activity
function activity_score(sub) {
    let stream_score = 0;
    if (!sub.subscribed) {
        stream_score = -1;
    } else {
        if (sub.pin_to_top) {
            stream_score += 2;
        }
        // Note: A pinned stream may accumulate a 3rd point if it is active
        if (stream_data.is_active(sub)) {
            stream_score += 1;
        }
    }
    return stream_score;
}

// Sort streams by ranking them by activity. If activity is equal,
// as defined bv activity_score, decide based on subscriber count.
exports.compare_by_activity = function (stream_a, stream_b) {
    let diff = activity_score(stream_b) - activity_score(stream_a);
    if (diff !== 0) {
        return diff;
    }
    diff = stream_b.subscribers.num_items() - stream_a.subscribers.num_items();
    if (diff !== 0) {
        return diff;
    }
    return util.strcmp(stream_a.name, stream_b.name);
};

exports.sort_streams = function (matches, query) {
    const name_results = util.prefix_sort(query, matches, function (x) { return x.name; });
    const desc_results
        = util.prefix_sort(query, name_results.rest, function (x) { return x.description; });

    // Streams that start with the query.
    name_results.matches = name_results.matches.sort(exports.compare_by_activity);
    // Streams with descriptions that start with the query.
    desc_results.matches = desc_results.matches.sort(exports.compare_by_activity);
    // Streams with names and descriptions that don't start with the query.
    desc_results.rest = desc_results.rest.sort(exports.compare_by_activity);

    return name_results.matches.concat(desc_results.matches.concat(desc_results.rest));
};

exports.sort_recipientbox_typeahead = function (query, matches, current_stream) {
    // input_text may be one or more pm recipients
    const cleaned = exports.get_cleaned_pm_recipients(query);
    query = cleaned[cleaned.length - 1];
    return exports.sort_recipients(matches, query, current_stream);
};

exports.sort_people_and_user_groups = function (query, matches) {
    const users = [];
    const groups = [];
    _.each(matches, function (match) {
        if (user_groups.is_user_group(match)) {
            groups.push(match);
        } else {
            users.push(match);
        }
    });

    const recipients = exports.sort_recipients(
        users,
        query,
        compose_state.stream_name(),
        compose_state.topic(),
        groups);
    return recipients;
};

window.typeahead_helper = exports;
