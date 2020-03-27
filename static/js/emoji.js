const util = require("./util");
const emoji_codes = require("../generated/emoji/emoji_codes.json");

// `emojis_by_name` is the central data source that is supposed to be
// used by every widget in the webapp for gathering data for displaying
// emojis. Emoji picker uses this data to derive data for its own use.
exports.emojis_by_name = new Map();

exports.all_realm_emojis = new Map();
exports.active_realm_emojis = new Map();
exports.default_emoji_aliases = new Map();

const emoticon_translations = (() => {
    /*

    Build a data structure that looks like something
    like this:

    [
        { regex: /(\:\))/g, replacement_text: ':slight_smile:' },
        { regex: /(\(\:)/g, replacement_text: ':slight_smile:' },
        { regex: /(\:\/)/g, replacement_text: ':confused:' },
        { regex: /(<3)/g, replacement_text: ':heart:' },
        { regex: /(\:\()/g, replacement_text: ':frown:' },
        { regex: /(\:\|)/g, replacement_text: ':expressionless:' }
    ]

        We build up this list of ~6 emoticon translations
        even if page_params.translate_emoticons is false, since
        that setting can be flipped via live update events.
        On the other hand, we assume that emoticon_conversions
        won't change until the next reload, which is fine for
        now (and we want to avoid creating new regexes on
        every new message).
    */

    const translations = [];
    for (const emoticon in emoji_codes.emoticon_conversions) {
        if (emoji_codes.emoticon_conversions.hasOwnProperty(emoticon)) {
            const replacement_text = emoji_codes.emoticon_conversions[emoticon];
            const regex = new RegExp('(' + util.escape_regexp(emoticon) + ')', 'g');

            translations.push({
                regex: regex,
                replacement_text: replacement_text,
            });
        }
    }

    return translations;
})();

const zulip_emoji = {
    id: 'zulip',
    emoji_name: 'zulip',
    emoji_url: '/static/generated/emoji/images/emoji/unicode/zulip.png',
    is_realm_emoji: true,
    deactivated: false,
};

exports.get_emoji_name = (codepoint) => {
    // get_emoji_name('1f384') === 'holiday_tree'
    return emoji_codes.codepoint_to_name[codepoint];
};

exports.get_emoji_codepoint = (emoji_name) => {
    // get_emoji_codepoint('avocado') === '1f951'
    return emoji_codes.name_to_codepoint[emoji_name];
};

exports.get_realm_emoji_url = (emoji_name) => {
    // If the emoji name is a realm emoji, returns the URL for it.
    // Returns undefined for unicode emoji.
    // get_realm_emoji_url('shrug') === '/user_avatars/2/emoji/images/31.png'

    const data = exports.active_realm_emojis.get(emoji_name);

    if (!data) {
        // Not all emojis have urls, plus the user
        // may have hand-typed an invalid emoji.
        // The caller can check the result for falsiness
        // and then try alternate ways of parsing the
        // emoji (in the case of markdown) or just do
        // whatever makes sense for the caller.
        return;
    }

    return data.emoji_url;
};

exports.update_emojis = function (realm_emojis) {
    // exports.all_realm_emojis is emptied before adding the realm-specific emoji
    // to it. This makes sure that in case of deletion, the deleted realm_emojis
    // don't persist in exports.active_realm_emojis.
    exports.all_realm_emojis.clear();
    exports.active_realm_emojis.clear();

    for (const data of Object.values(realm_emojis)) {
        exports.all_realm_emojis.set(data.id, {
            id: data.id,
            emoji_name: data.name,
            emoji_url: data.source_url,
            deactivated: data.deactivated,
        });
        if (data.deactivated !== true) {
            exports.active_realm_emojis.set(data.name, {
                id: data.id,
                emoji_name: data.name,
                emoji_url: data.source_url,
            });
        }
    }
    // Add the Zulip emoji to the realm emojis list
    exports.all_realm_emojis.set("zulip", zulip_emoji);
    exports.active_realm_emojis.set("zulip", zulip_emoji);

    exports.build_emoji_data(exports.active_realm_emojis);
};

exports.initialize = function initialize() {
    for (const value of emoji_codes.names) {
        const base_name = exports.get_emoji_codepoint(value);

        if (exports.default_emoji_aliases.has(base_name)) {
            exports.default_emoji_aliases.get(base_name).push(value);
        } else {
            exports.default_emoji_aliases.set(base_name, [value]);
        }
    }

    exports.update_emojis(page_params.realm_emoji);
};

exports.build_emoji_data = function (realm_emojis) {
    exports.emojis_by_name.clear();
    for (const [realm_emoji_name, realm_emoji] of realm_emojis) {
        const emoji_dict = {
            name: realm_emoji_name,
            display_name: realm_emoji_name,
            aliases: [realm_emoji_name],
            is_realm_emoji: true,
            url: realm_emoji.emoji_url,
            has_reacted: false,
        };
        exports.emojis_by_name.set(realm_emoji_name, emoji_dict);
    }

    for (const codepoints of Object.values(emoji_codes.emoji_catalog)) {
        for (const codepoint of codepoints) {
            if (emoji_codes.codepoint_to_name.hasOwnProperty(codepoint)) {
                const emoji_name = exports.get_emoji_name(codepoint);
                if (!exports.emojis_by_name.has(emoji_name)) {
                    const emoji_dict = {
                        name: emoji_name,
                        display_name: emoji_name,
                        aliases: exports.default_emoji_aliases.get(codepoint),
                        is_realm_emoji: false,
                        emoji_code: codepoint,
                        has_reacted: false,
                    };
                    exports.emojis_by_name.set(emoji_name, emoji_dict);
                }
            }
        }
    }
};

exports.build_emoji_upload_widget = function () {

    const get_file_input = function () {
        return $('#emoji_file_input');
    };

    const file_name_field = $('#emoji-file-name');
    const input_error = $('#emoji_file_input_error');
    const clear_button = $('#emoji_image_clear_button');
    const upload_button = $('#emoji_upload_button');

    return upload_widget.build_widget(
        get_file_input,
        file_name_field,
        input_error,
        clear_button,
        upload_button
    );
};

exports.get_canonical_name = function (emoji_name) {
    if (exports.active_realm_emojis.has(emoji_name)) {
        return emoji_name;
    }
    if (!emoji_codes.name_to_codepoint.hasOwnProperty(emoji_name)) {
        blueslip.error("Invalid emoji name: " + emoji_name);
        return;
    }
    const codepoint = exports.get_emoji_codepoint(emoji_name);

    return exports.get_emoji_name(codepoint);
};

exports.get_emoticon_translations = () => emoticon_translations;

window.emoji = exports;
