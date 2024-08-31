import type {Option} from "./dropdown_widget";
import {$t} from "./i18n";
import * as util from "./util";

export type SavedReplies = {
    id: number;
    title: string;
    content: string;
    date_created: number;
};

export const ADD_SAVED_REPLY_OPTION_ID = -1;
let my_saved_replies: SavedReplies[] = [];

export function set_saved_replies(saved_replies: SavedReplies[]): void {
    my_saved_replies = saved_replies;
    my_saved_replies.sort((a, b) => util.strcmp(a.title.toLowerCase(), b.title.toLowerCase()));
}

export function get_saved_replies(): SavedReplies[] {
    return my_saved_replies;
}

export function add_saved_reply(saved_reply: SavedReplies): void {
    my_saved_replies.push(saved_reply);
    my_saved_replies.sort((a, b) => util.strcmp(a.title.toLowerCase(), b.title.toLowerCase()));
}

export function remove_saved_reply(saved_reply_id: number): void {
    my_saved_replies = my_saved_replies.filter((s) => s.id !== saved_reply_id);
}

export function get_options_for_dropdown_widget(): Option[] {
    const saved_replies = my_saved_replies.map((saved_reply) => ({
        unique_id: saved_reply.id,
        name: saved_reply.title,
        description: saved_reply.content,
        bold_current_selection: true,
        has_delete_icon: true,
    }));

    // Option for creating a new saved reply.
    saved_replies.unshift({
        unique_id: ADD_SAVED_REPLY_OPTION_ID,
        name: $t({defaultMessage: "Add a new saved reply"}),
        description: "",
        bold_current_selection: true,
        has_delete_icon: false,
    });
    return saved_replies;
}
