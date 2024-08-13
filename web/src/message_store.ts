import _ from "lodash";

import * as blueslip from "./blueslip";
import * as people from "./people";
import type {Submessage} from "./submessage";
import type {TopicLink} from "./types";
import type {UserStatusEmojiInfo} from "./user_status";

const stored_messages = new Map<number, Message>();

export type MatchedMessage = {
    match_content?: string | undefined;
    match_subject?: string | undefined;
};

export type MessageReactionType = "unicode_emoji" | "realm_emoji" | "zulip_extra_emoji";

export type DisplayRecipientUser = {
    email: string;
    full_name: string;
    id: number;
    is_mirror_dummy?: boolean;
    unknown_local_echo_user?: boolean;
};

export type DisplayRecipient = string | DisplayRecipientUser[];

export type MessageEditHistoryEntry = {
    user_id: number | null;
    timestamp: number;
    prev_content?: string;
    prev_rendered_content?: string;
    prev_rendered_content_version?: number;
    prev_stream?: number;
    prev_topic?: string;
    stream?: number;
    topic?: string;
};

export type MessageReaction = {
    emoji_name: string;
    emoji_code: string;
    reaction_type: MessageReactionType;
    user_id: number;
};

export type RawMessage = {
    avatar_url: string | null;
    client: string;
    content: string;
    content_type: "text/html";
    display_recipient: DisplayRecipient;
    edit_history?: MessageEditHistoryEntry[];
    id: number;
    is_me_message: boolean;
    last_edit_timestamp?: number;
    reactions: MessageReaction[];
    recipient_id: number;
    sender_email: string;
    sender_full_name: string;
    sender_id: number;
    sender_realm_str: string;
    submessages: Submessage[];
    timestamp: number;
    flags: string[];
} & (
    | {
          type: "private";
      }
    | {
          type: "stream";
          stream_id: number;
          // Messages that come from the server use `subject`.
          // Messages that come from `send_message` use `topic`.
          subject?: string;
          topic?: string;
          topic_links: TopicLink[];
      }
) &
    MatchedMessage;

// We add these boolean properties to Raw message in
// `message_store.convert_raw_message_to_message_with_booleans` method.
export type MessageWithBooleans = (
    | Omit<RawMessage & {type: "private"}, "flags">
    | Omit<RawMessage & {type: "stream"}, "flags">
) & {
    unread: boolean;
    historical: boolean;
    starred: boolean;
    mentioned: boolean;
    mentioned_me_directly: boolean;
    stream_wildcard_mentioned: boolean;
    topic_wildcard_mentioned: boolean;
    collapsed: boolean;
    condensed?: boolean;
    alerted: boolean;
};

export type MessageCleanReaction = {
    class: string;
    count: number;
    emoji_alt_code: boolean;
    emoji_code: string;
    emoji_name: string;
    is_realm_emoji: boolean;
    label: string;
    local_id: string;
    reaction_type: "zulip_extra_emoji" | "realm_emoji" | "unicode_emoji";
    user_ids: number[];
    vote_text: string;
};

export type Message = (
    | Omit<MessageWithBooleans & {type: "private"}, "reactions">
    | Omit<MessageWithBooleans & {type: "stream"}, "reactions" | "subject">
) & {
    clean_reactions: Map<string, MessageCleanReaction>;

    locally_echoed?: boolean;
    raw_content?: string;

    // Added in `message_helper.process_new_message`.
    sent_by_me: boolean;
    reply_to: string;

    // These properties are set and used in `message_list_view.js`.
    // TODO: It would be nice if we could not store these on the message
    // object and only reference them within `message_list_view`.
    message_reactions?: MessageCleanReaction[];
    url?: string;

    // Used in `markdown.js`, `server_events.js`, and
    // `convert_raw_message_to_message_with_booleans`
    flags?: string[];

    small_avatar_url?: string; // Used in `message_avatar.hbs`
    status_emoji_info?: UserStatusEmojiInfo | undefined; // Used in `message_body.hbs`
} & (
        | {
              type: "private";
              is_private: true;
              is_stream: false;
              pm_with_url: string;
              to_user_ids: string;
              display_reply_to: string;
          }
        | {
              type: "stream";
              is_private: false;
              is_stream: true;
              stream: string;
              topic: string;
              display_reply_to: undefined;
          }
    );

export function update_message_cache(message: Message): void {
    // You should only call this from message_helper (or in tests).
    stored_messages.set(message.id, message);
}

export function get_cached_message(message_id: number): Message | undefined {
    // You should only call this from message_helper.
    // Use the get() wrapper below for most other use cases.
    return stored_messages.get(message_id);
}

export function clear_for_testing(): void {
    stored_messages.clear();
}

export function get(message_id: number): Message | undefined {
    return stored_messages.get(message_id);
}

export function get_pm_emails(message: Message | MessageWithBooleans): string {
    const user_ids = people.pm_with_user_ids(message) ?? [];
    const emails = user_ids
        .map((user_id) => {
            const person = people.maybe_get_user_by_id(user_id);
            if (!person) {
                blueslip.error("Unknown user id", {user_id});
                return "?";
            }
            return person.email;
        })
        .sort();

    return emails.join(", ");
}

export function get_pm_full_names(user_ids: number[]): string {
    user_ids = people.sorted_other_user_ids(user_ids);
    const names = people.get_display_full_names(user_ids).sort();

    return names.join(", ");
}

export function convert_raw_message_to_message_with_booleans(
    message: RawMessage,
): MessageWithBooleans {
    const flags = message.flags ?? [];

    function convert_flag(flag_name: string): boolean {
        return flags.includes(flag_name);
    }

    const converted_flags = {
        unread: !convert_flag("read"),
        historical: convert_flag("historical"),
        starred: convert_flag("starred"),
        mentioned:
            convert_flag("mentioned") ||
            convert_flag("stream_wildcard_mentioned") ||
            convert_flag("topic_wildcard_mentioned"),
        mentioned_me_directly: convert_flag("mentioned"),
        stream_wildcard_mentioned: convert_flag("stream_wildcard_mentioned"),
        topic_wildcard_mentioned: convert_flag("topic_wildcard_mentioned"),
        collapsed: convert_flag("collapsed"),
        alerted: convert_flag("has_alert_word"),
    };

    // Once we have set boolean flags here, the `flags` attribute is
    // just a distraction, so we delete it.  (All the downstream code
    // uses booleans.)

    // We have to return these separately because of how the `MessageWithBooleans`
    // type is set up.
    if (message.type === "private") {
        return {
            ..._.omit(message, "flags"),
            ...converted_flags,
        };
    }
    return {
        ..._.omit(message, "flags"),
        ...converted_flags,
    };
}

export function update_booleans(message: Message, flags: string[]): void {
    // When we get server flags for local echo or message edits,
    // we are vulnerable to race conditions, so only update flags
    // that are driven by message content.
    function convert_flag(flag_name: string): boolean {
        return flags.includes(flag_name);
    }

    message.mentioned =
        convert_flag("mentioned") ||
        convert_flag("stream_wildcard_mentioned") ||
        convert_flag("topic_wildcard_mentioned");
    message.mentioned_me_directly = convert_flag("mentioned");
    message.stream_wildcard_mentioned = convert_flag("stream_wildcard_mentioned");
    message.topic_wildcard_mentioned = convert_flag("topic_wildcard_mentioned");
    message.alerted = convert_flag("has_alert_word");
}

export function update_sender_full_name(user_id: number, new_name: string): void {
    for (const msg of stored_messages.values()) {
        if (msg.sender_id && msg.sender_id === user_id) {
            msg.sender_full_name = new_name;
        }
    }
}

export function update_small_avatar_url(user_id: number, new_url: string): void {
    for (const msg of stored_messages.values()) {
        if (msg.sender_id && msg.sender_id === user_id) {
            msg.small_avatar_url = new_url;
        }
    }
}

export function update_stream_name(stream_id: number, new_name: string): void {
    for (const msg of stored_messages.values()) {
        if (msg.type === "stream" && msg.stream_id === stream_id) {
            msg.display_recipient = new_name;
        }
    }
}

export function update_status_emoji_info(
    user_id: number,
    new_info: UserStatusEmojiInfo | undefined,
): void {
    for (const msg of stored_messages.values()) {
        if (msg.sender_id && msg.sender_id === user_id) {
            msg.status_emoji_info = new_info;
        }
    }
}

export function reify_message_id({old_id, new_id}: {old_id: number; new_id: number}): void {
    const message = stored_messages.get(old_id);
    if (message !== undefined) {
        message.id = new_id;
        message.locally_echoed = false;
        stored_messages.set(new_id, message);
        stored_messages.delete(old_id);
    }
}

export function remove(message_ids: number[]): void {
    for (const message_id of message_ids) {
        stored_messages.delete(message_id);
    }
}
