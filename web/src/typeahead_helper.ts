import Handlebars from "handlebars/runtime";
import _ from "lodash";
import assert from "minimalistic-assert";

import * as typeahead from "../shared/src/typeahead";
import type {EmojiSuggestion} from "../shared/src/typeahead";
import render_typeahead_list_item from "../templates/typeahead_list_item.hbs";

import {MAX_ITEMS} from "./bootstrap_typeahead";
import * as buddy_data from "./buddy_data";
import * as compose_state from "./compose_state";
import type {LanguageSuggestion, SlashCommandSuggestion} from "./composebox_typeahead";
import type {InputPillContainer} from "./input_pill";
import * as people from "./people";
import type {PseudoMentionUser, User} from "./people";
import * as pm_conversations from "./pm_conversations";
import * as pygments_data from "./pygments_data";
import * as recent_senders from "./recent_senders";
import {realm} from "./state_data";
import * as stream_data from "./stream_data";
import * as stream_list_sort from "./stream_list_sort";
import type {StreamPill, StreamPillData} from "./stream_pill";
import type {StreamSubscription} from "./sub_store";
import type {UserGroupPill, UserGroupPillData} from "./user_group_pill";
import * as user_groups from "./user_groups";
import type {UserGroup} from "./user_groups";
import type {UserPill, UserPillData} from "./user_pill";
import * as user_status from "./user_status";
import type {UserStatusEmojiInfo} from "./user_status";
import * as util from "./util";

export type UserOrMention =
    | {type: "broadcast"; user: PseudoMentionUser}
    | {type: "user"; user: User};
export type UserOrMentionPillData = UserOrMention & {
    is_silent?: boolean;
};

export type CombinedPill = StreamPill | UserGroupPill | UserPill;
export type CombinedPillContainer = InputPillContainer<CombinedPill>;

export type GroupSettingPill = UserGroupPill | UserPill;
export type GroupSettingPillContainer = InputPillContainer<GroupSettingPill>;

export function build_highlight_regex(query: string): RegExp {
    const regex = new RegExp("(" + _.escapeRegExp(query) + ")", "ig");
    return regex;
}

export function highlight_with_escaping_and_regex(regex: RegExp, item: string): string {
    // if regex is empty return entire item escaped
    if (regex.source === "()") {
        return Handlebars.Utils.escapeExpression(item);
    }

    // We need to assemble this manually (as opposed to doing 'join') because we need to
    // (1) escape all the pieces and (2) the regex is case-insensitive, and we need
    // to know the case of the content we're replacing (you can't just use a bolded
    // version of 'query')

    const pieces = item.split(regex).filter(Boolean);
    let result = "";

    for (const [i, piece] of pieces.entries()) {
        if (regex.test(piece) && (i === 0 || pieces[i - 1]!.endsWith(" "))) {
            // only highlight if the matching part is a word prefix, ie
            // if it is the 1st piece or if there was a space before it
            result += "<strong>" + Handlebars.Utils.escapeExpression(piece) + "</strong>";
        } else {
            result += Handlebars.Utils.escapeExpression(piece);
        }
    }

    return result;
}

export function make_query_highlighter(query: string): (phrase: string) => string {
    query = query.toLowerCase();

    const regex = build_highlight_regex(query);

    return function (phrase) {
        return highlight_with_escaping_and_regex(regex, phrase);
    };
}

type StreamData = {
    invite_only: boolean;
    is_web_public: boolean;
    color: string;
    name: string;
    description: string;
    rendered_description: string;
    subscribed: boolean;
};

export function render_typeahead_item(args: {
    primary?: string | undefined;
    is_person?: boolean;
    img_src?: string;
    status_emoji_info?: UserStatusEmojiInfo | undefined;
    secondary?: string | null;
    secondary_html?: string | undefined;
    pronouns?: string | undefined;
    is_user_group?: boolean;
    stream?: StreamData;
    is_unsubscribed?: boolean;
    emoji_code?: string | undefined;
}): string {
    const has_image = args.img_src !== undefined;
    const has_status = args.status_emoji_info !== undefined;
    const has_secondary = args.secondary !== undefined;
    const has_secondary_html = args.secondary_html !== undefined;
    const has_pronouns = args.pronouns !== undefined;
    return render_typeahead_list_item({
        ...args,
        has_image,
        has_status,
        has_secondary,
        has_secondary_html,
        has_pronouns,
    });
}

export function render_person(person: UserPillData | UserOrMentionPillData): string {
    if (person.type === "broadcast") {
        return render_typeahead_item({
            primary: person.user.special_item_text,
            is_person: true,
        });
    }
    const user_circle_class = buddy_data.get_user_circle_class(person.user.user_id);

    const avatar_url = people.small_avatar_url_for_person(person.user);

    const status_emoji_info = user_status.get_status_emoji(person.user.user_id);

    const PRONOUNS_ID = realm.custom_profile_field_types.PRONOUNS.id;
    const pronouns_list = people.get_custom_fields_by_type(person.user.user_id, PRONOUNS_ID);

    const pronouns = pronouns_list?.[0]?.value;

    const typeahead_arguments = {
        primary: person.user.full_name,
        img_src: avatar_url,
        user_circle_class,
        is_person: true,
        status_emoji_info,
        should_add_guest_user_indicator: people.should_add_guest_user_indicator(
            person.user.user_id,
        ),
        pronouns,
        secondary: person.user.delivery_email,
    };

    return render_typeahead_item(typeahead_arguments);
}

export function render_user_group(user_group: {name: string; description: string}): string {
    return render_typeahead_item({
        primary: user_groups.get_display_group_name(user_group.name),
        secondary: user_group.description,
        is_user_group: true,
    });
}

export function render_person_or_user_group(
    item: UserGroupPillData | UserPillData | UserOrMentionPillData,
): string {
    if (item.type === "user_group") {
        return render_user_group(item);
    }

    return render_person(item);
}

export function render_stream(stream: StreamData): string {
    return render_typeahead_item({
        secondary_html: stream.rendered_description,
        stream,
        is_unsubscribed: !stream.subscribed,
    });
}

export function render_emoji(item: EmojiSuggestion): string {
    const args = {
        is_emoji: true,
        primary: item.emoji_name.replaceAll("_", " "),
    };

    if (item.emoji_url) {
        return render_typeahead_item({
            ...args,
            img_src: item.emoji_url,
        });
    }
    return render_typeahead_item({
        ...args,
        emoji_code: item.emoji_code,
    });
}

export function sorter<T>(query: string, objs: T[], get_item: (x: T) => string): T[] {
    const results = typeahead.triage(query, objs, get_item);
    return [...results.matches, ...results.rest];
}

export function compare_by_pms(user_a: User, user_b: User): number {
    const count_a = people.get_recipient_count(user_a);
    const count_b = people.get_recipient_count(user_b);

    if (count_a > count_b) {
        return -1;
    } else if (count_a < count_b) {
        return 1;
    }

    const a_is_partner = pm_conversations.is_partner(user_a.user_id);
    const b_is_partner = pm_conversations.is_partner(user_b.user_id);

    // This code will never run except in the rare case that one has no
    // recent DM message history with a user, but does have some older
    // message history that's outside the "recent messages only"
    // data set powering people.get_recipient_count.
    if (a_is_partner && !b_is_partner) {
        return -1;
    } else if (!a_is_partner && b_is_partner) {
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
}

export function compare_people_for_relevance(
    person_a: UserOrMentionPillData | UserPillData,
    person_b: UserOrMentionPillData | UserPillData,
    compare_by_current_conversation?: (user_a: User, user_b: User) => number,
    current_stream_id?: number,
): number {
    // give preference to "all", "everyone" or "stream"
    if (compose_state.get_message_type() !== "private") {
        if (person_a.type === "broadcast") {
            if (person_b.type === "broadcast") {
                return person_a.user.idx - person_b.user.idx;
            }
            return -1;
        } else if (person_b.type === "broadcast") {
            return 1;
        }
    } else {
        if (person_a.type === "broadcast") {
            if (person_b.type === "broadcast") {
                return person_a.user.idx - person_b.user.idx;
            }
            return 1;
        } else if (person_b.type === "broadcast") {
            return -1;
        }
    }

    // Now handle actual people users.
    // give preference to subscribed users first
    if (current_stream_id !== undefined) {
        const a_is_sub = stream_data.is_user_subscribed(current_stream_id, person_a.user.user_id);
        const b_is_sub = stream_data.is_user_subscribed(current_stream_id, person_b.user.user_id);

        if (a_is_sub && !b_is_sub) {
            return -1;
        } else if (!a_is_sub && b_is_sub) {
            return 1;
        }
    }

    if (compare_by_current_conversation !== undefined) {
        const preference = compare_by_current_conversation(person_a.user, person_b.user);
        if (preference !== 0) {
            return preference;
        }
    }

    return compare_by_pms(person_a.user, person_b.user);
}

export function sort_people_for_relevance<UserType extends UserOrMentionPillData | UserPillData>(
    objs: UserType[],
    current_stream_id?: number,
    current_topic?: string,
): UserType[] {
    // If sorting for recipientbox typeahead and not viewing a stream / topic, then current_stream = ""
    const current_stream =
        current_stream_id !== undefined ? stream_data.get_sub_by_id(current_stream_id) : undefined;
    if (current_stream === undefined) {
        objs.sort((person_a, person_b) => compare_people_for_relevance(person_a, person_b));
    } else {
        assert(current_stream_id !== undefined);
        assert(current_topic !== undefined);
        objs.sort((person_a, person_b) =>
            compare_people_for_relevance(
                person_a,
                person_b,
                (user_a, user_b) =>
                    recent_senders.compare_by_recency(
                        user_a,
                        user_b,
                        current_stream_id,
                        current_topic,
                    ),
                current_stream_id,
            ),
        );
    }

    return objs;
}

function compare_language_by_popularity(lang_a: string, lang_b: string): number {
    const lang_a_data = pygments_data.langs[lang_a];
    const lang_b_data = pygments_data.langs[lang_b];

    // If a "language" doesn't have a popularity score, that "language" is
    // probably a custom language created in the Code Playground feature. That
    // custom language might not even be an actual programming language. Some
    // users simply use the Code Playground feature as a shortcut mechanism.
    // Like the report in issue #23935 is suggesting. Also, because Code
    // Playground doesn't actually allow custom syntax highlighting, any custom
    // languages are probably more likely to be attempts to create a shortcut
    // mechanism. In that case, they're more like custom keywords rather than
    // languages.
    //
    // We need to make a choice for the ordering of those custom languages when
    // compared with languages available in pygment. It might come down to
    // individual usage which one is more valuable.
    //
    // If most of the time a user uses code block for syntax highlighting, then
    // sorting custom language later on makes sense. If most of the time a user
    // uses a code block as a shortcut mechanism, then they might want custom
    // language earlier on.
    //
    // At this time, we chose to sort custom languages after pygment languages
    // due to the following reasons:
    // - Code blocks are originally used to display code with syntax
    //   highlighting. Users can add Code Playground custom language, without
    //   having the autocomplete ordering they're used to being affected.
    // - Users can design their custom language name to be more unique or using
    //   characters such that they appear faster in autocomplete. Therefore,
    //   they have a way to purposely affect the system to suit their
    //   autocomplete ordering preference.
    //
    // If in the future we find that many users have a need for a configurable
    // setting, then we could create one. But for now, sorting after pygment
    // languages seem sensible.
    if (!lang_a_data && !lang_b_data) {
        return 0; // Neither have popularity, so they tie.
    } else if (!lang_a_data) {
        return 1; // lang_a doesn't have popularity, so sort a after b.
    } else if (!lang_b_data) {
        return -1; // lang_b doesn't have popularity, so sort a before b.
    }

    return lang_b_data.priority - lang_a_data.priority;
}

// This function compares two languages first by their popularity, then if
// there is a tie on popularity, then compare alphabetically to break the tie.
export function compare_language(lang_a: string, lang_b: string): number {
    let diff = compare_language_by_popularity(lang_a, lang_b);

    // Check to see if there is a tie. If there is, then use alphabetical order
    // to break the tie.
    if (diff === 0) {
        diff = util.strcmp(lang_a, lang_b);
    }

    return diff;
}

function retain_unique_language_aliases(matches: string[]): string[] {
    // We make the typeahead a little more nicer but only showing one alias per language.
    // For example if the user searches for prefix "j", then the typeahead list should contain
    // "javascript" only, and not "js" and "javascript".
    const seen_aliases = new Set();
    const unique_aliases = [];
    for (const lang of matches) {
        // The matched list is already sorted based on popularity and has exact matches
        // at the top, so we don't need to worry about sorting again.
        const canonical_name = pygments_data.langs[lang]?.pretty_name ?? lang;
        if (!seen_aliases.has(canonical_name)) {
            seen_aliases.add(canonical_name);
            unique_aliases.push(lang);
        }
    }
    return unique_aliases;
}

export function sort_languages(matches: LanguageSuggestion[], query: string): LanguageSuggestion[] {
    const languages = matches.map((object) => object.language);
    const results = typeahead.triage(query, languages, (x) => x, compare_language);
    const unique_languages = retain_unique_language_aliases([...results.matches, ...results.rest]);
    return unique_languages.map((language) => ({
        language,
        type: "syntax",
    }));
}

export function sort_recipients<UserType extends UserOrMentionPillData | UserPillData>({
    users,
    query,
    current_stream_id,
    current_topic,
    groups = [],
    max_num_items = MAX_ITEMS,
}: {
    users: UserType[];
    query: string;
    current_stream_id?: number | undefined;
    current_topic?: string | undefined;
    groups?: UserGroupPillData[];
    max_num_items?: number | undefined;
}): (UserType | UserGroupPillData)[] {
    function sort_relevance(items: UserType[]): UserType[] {
        return sort_people_for_relevance(items, current_stream_id, current_topic);
    }

    const users_name_results = typeahead.triage_raw(query, users, (p) => p.user.full_name);
    const users_name_good_matches = [
        ...users_name_results.exact_matches,
        ...users_name_results.begins_with_case_sensitive_matches,
        ...users_name_results.begins_with_case_insensitive_matches,
    ];
    const users_name_okay_matches = [...users_name_results.word_boundary_matches];

    const email_results = typeahead.triage_raw(
        query,
        users_name_results.no_matches,
        (p) => p.user.email,
    );
    const email_good_matches = [
        ...email_results.exact_matches,
        ...email_results.begins_with_case_sensitive_matches,
        ...email_results.begins_with_case_insensitive_matches,
    ];
    const email_okay_matches = [...email_results.word_boundary_matches];

    const groups_results = typeahead.triage_raw(query, groups, (g) => g.name);
    const groups_good_matches = [
        ...groups_results.exact_matches,
        ...groups_results.begins_with_case_sensitive_matches,
        ...groups_results.begins_with_case_insensitive_matches,
    ];
    const groups_okay_matches = [...groups_results.word_boundary_matches];

    const best_users = (): UserType[] => [
        ...sort_relevance(users_name_good_matches),
        ...sort_relevance(users_name_okay_matches),
    ];
    const best_groups = (): UserGroupPillData[] => [...groups_good_matches, ...groups_okay_matches];
    const ok_users = (): UserType[] => [
        ...sort_relevance(email_good_matches),
        ...sort_relevance(email_okay_matches),
    ];
    const worst_users = (): UserType[] => sort_relevance(email_results.no_matches);
    const worst_groups = (): UserGroupPillData[] => groups_results.no_matches;

    const getters: (
        | {
              getter: () => UserType[];
              type: "users";
          }
        | {
              getter: () => UserGroupPillData[];
              type: "groups";
          }
    )[] = [
        {
            getter: best_users,
            type: "users",
        },
        {
            getter: best_groups,
            type: "groups",
        },
        {
            getter: ok_users,
            type: "users",
        },
        {
            getter: worst_users,
            type: "users",
        },
        {
            getter: worst_groups,
            type: "groups",
        },
    ];

    // We suggest only the first matching stream wildcard mention,
    // irrespective of how many equivalent stream wildcard mentions match.
    const recipients: (UserType | UserGroupPillData)[] = [];
    let stream_wildcard_mention_included = false;

    function add_user_recipients(items: UserType[]): void {
        for (const item of items) {
            if (
                item.type !== "broadcast" ||
                item.user.email === "topic" ||
                !stream_wildcard_mention_included
            ) {
                recipients.push(item);
                if (item.type === "broadcast" && item.user.email !== "topic") {
                    stream_wildcard_mention_included = true;
                }
            }
        }
    }

    function add_group_recipients(items: UserGroupPillData[]): void {
        for (const item of items) {
            recipients.push(item);
        }
    }

    for (const getter of getters) {
        /*
            The following optimization is important for large realms.
            If we know we're only showing 5 suggestions, and we
            get 5 matches from `best_users`, then we want to avoid
            calling the expensive sorts for `ok_users` and `worst_users`,
            since they just get dropped.
        */
        if (recipients.length >= max_num_items) {
            break;
        }
        if (getter.type === "users") {
            add_user_recipients(getter.getter());
        } else {
            add_group_recipients(getter.getter());
        }
    }

    // We don't push exact matches to the top, like we do with other
    // typeaheads, because in open organizations, it's not uncommon to
    // have a bunch of inactive users with display names that are just
    // FirstName, which we don't want to artificially prioritize over the
    // the lone active user whose name is FirstName LastName.
    return recipients.slice(0, max_num_items);
}

export function compare_setting_options(
    option_a: UserPillData | UserGroupPillData,
    option_b: UserPillData | UserGroupPillData,
    target_group: UserGroup | undefined,
): number {
    if (option_a.type === "user_group" && option_b.type === "user") {
        return -1;
    }

    if (option_b.type === "user_group" && option_a.type === "user") {
        return 1;
    }

    if (option_a.type === "user_group" && option_b.type === "user_group") {
        const user_group_a = user_groups.get_user_group_from_id(option_a.id);
        const user_group_b = user_groups.get_user_group_from_id(option_b.id);

        if (user_group_a.is_system_group && !user_group_b.is_system_group) {
            return -1;
        }

        if (user_group_b.is_system_group && !user_group_a.is_system_group) {
            return 1;
        }

        if (user_group_a.name < user_group_b.name) {
            return -1;
        }

        return 1;
    }

    assert(option_a.type === "user");
    assert(option_b.type === "user");

    if (target_group !== undefined) {
        if (
            !target_group.members.has(option_a.user.user_id) &&
            target_group.members.has(option_b.user.user_id)
        ) {
            return 1;
        }

        if (
            target_group.members.has(option_a.user.user_id) &&
            !target_group.members.has(option_b.user.user_id)
        ) {
            return -1;
        }
    }

    if (option_a.user.full_name < option_b.user.full_name) {
        return -1;
    } else if (option_a.user.full_name === option_b.user.full_name) {
        return 0;
    }

    return 1;
}

export function sort_group_setting_options({
    users,
    query,
    groups,
    target_group,
}: {
    users: UserPillData[];
    query: string;
    groups: UserGroupPillData[];
    target_group: UserGroup | undefined;
}): (UserPillData | UserGroupPillData)[] {
    function sort_group_setting_items(
        objs: (UserPillData | UserGroupPillData)[],
    ): (UserPillData | UserGroupPillData)[] {
        objs.sort((option_a, option_b) =>
            compare_setting_options(option_a, option_b, target_group),
        );
        return objs;
    }

    const users_name_results = typeahead.triage_raw(query, users, (p) => p.user.full_name);
    const email_results = typeahead.triage_raw(
        query,
        users_name_results.no_matches,
        (p) => p.user.email,
    );
    const groups_results = typeahead.triage_raw(query, groups, (g) => g.name);

    const exact_matches = sort_group_setting_items([
        ...groups_results.exact_matches,
        ...users_name_results.exact_matches,
        ...email_results.exact_matches,
    ]);

    const prefix_matches = sort_group_setting_items([
        ...groups_results.begins_with_case_sensitive_matches,
        ...groups_results.begins_with_case_insensitive_matches,
        ...users_name_results.begins_with_case_sensitive_matches,
        ...users_name_results.begins_with_case_insensitive_matches,
        ...email_results.begins_with_case_sensitive_matches,
        ...email_results.begins_with_case_insensitive_matches,
    ]);

    const word_boundary_matches = sort_group_setting_items([
        ...groups_results.word_boundary_matches,
        ...users_name_results.word_boundary_matches,
        ...email_results.word_boundary_matches,
    ]);

    const no_matches = sort_group_setting_items([
        ...groups_results.no_matches,
        ...email_results.no_matches,
    ]);

    const getters: {
        getter: (UserPillData | UserGroupPillData)[];
    }[] = [
        {
            getter: exact_matches,
        },
        {
            getter: prefix_matches,
        },
        {
            getter: word_boundary_matches,
        },
        {
            getter: no_matches,
        },
    ];

    const setting_options: (UserPillData | UserGroupPillData)[] = [];

    for (const getter of getters) {
        if (setting_options.length >= MAX_ITEMS) {
            break;
        }
        for (const item of getter.getter) {
            setting_options.push(item);
        }
    }

    return setting_options.slice(0, MAX_ITEMS);
}

type SlashCommand = {
    name: string;
};

function slash_command_comparator(
    slash_command_a: SlashCommand,
    slash_command_b: SlashCommand,
): number {
    if (slash_command_a.name < slash_command_b.name) {
        return -1;
    } else if (slash_command_a.name > slash_command_b.name) {
        return 1;
    }
    /* istanbul ignore next */
    return 0;
}

export function sort_slash_commands(
    matches: SlashCommandSuggestion[],
    query: string,
): SlashCommandSuggestion[] {
    // We will likely want to in the future make this sort the
    // just-`/` commands by something approximating usefulness.
    const results = typeahead.triage(query, matches, (x) => x.name, slash_command_comparator);

    return [...results.matches, ...results.rest];
}

function activity_score(sub: StreamSubscription): number {
    // We assign the highest score to the stream being composed
    // to, and the lowest score to unsubscribed streams. For others,
    // we prioritise pinned unmuted streams > unpinned unmuted streams
    // > pinned muted streams > unpinned muted streams, using recent
    // activity as a tiebreaker.
    if (sub.name === compose_state.stream_name()) {
        return 8;
    }
    if (!sub.subscribed) {
        return -1;
    }

    let stream_score = 0;
    if (!sub.is_muted) {
        stream_score += 4;
    }
    if (sub.pin_to_top) {
        stream_score += 2;
    }
    if (stream_list_sort.has_recent_activity(sub)) {
        stream_score += 1;
    }
    return stream_score;
}

// Sort streams by ranking them by activity. If activity is equal,
// as defined bv activity_score, decide based on our weekly traffic
// stats.
export function compare_by_activity(
    stream_a: StreamSubscription,
    stream_b: StreamSubscription,
): number {
    let diff = activity_score(stream_b) - activity_score(stream_a);
    if (diff !== 0) {
        return diff;
    }
    diff = (stream_b.stream_weekly_traffic ?? 0) - (stream_a.stream_weekly_traffic ?? 0);
    if (diff !== 0) {
        return diff;
    }
    return util.strcmp(stream_a.name, stream_b.name);
}

function compare_by_name(stream_a: StreamSubscription, stream_b: StreamSubscription): number {
    return util.strcmp(stream_a.name, stream_b.name);
}

export function sort_streams(matches: StreamPillData[], query: string): StreamPillData[] {
    const name_results = typeahead.triage(query, matches, (x) => x.name, compare_by_activity);
    const desc_results = typeahead.triage(
        query,
        name_results.rest,
        (x) => x.description,
        compare_by_activity,
    );

    return [...name_results.matches, ...desc_results.matches, ...desc_results.rest];
}

export function sort_streams_by_name(matches: StreamPillData[], query: string): StreamPillData[] {
    const results = typeahead.triage(query, matches, (x) => x.name, compare_by_name);
    return [...results.matches, ...results.rest];
}

export function query_matches_person(
    query: string,
    person: UserPillData | UserOrMentionPillData,
): boolean {
    if (typeahead.query_matches_string_in_order(query, person.user.full_name, " ")) {
        return true;
    }
    if (person.type === "user" && Boolean(person.user.delivery_email)) {
        return typeahead.query_matches_string_in_order(
            query,
            people.get_visible_email(person.user),
            " ",
        );
    }
    return false;
}

export function query_matches_name(
    query: string,
    user_group_or_stream: UserGroupPillData | StreamPillData,
): boolean {
    return typeahead.query_matches_string_in_order(query, user_group_or_stream.name, " ");
}

export function query_matches_group_name(query: string, user_group: UserGroupPillData): boolean {
    return typeahead.query_matches_string_in_order(
        query,
        user_groups.get_display_group_name(user_group.name),
        "",
    );
}
