import assert from "minimalistic-assert";

import render_input_pill from "../templates/input_pill.hbs";

import * as input_pill from "./input_pill";
import type {GroupSettingPill, GroupSettingPillContainer} from "./typeahead_helper";
import * as user_group_pill from "./user_group_pill";
import * as user_groups from "./user_groups";
import * as user_pill from "./user_pill";

export function create_item_from_text(
    text: string,
    current_items: GroupSettingPill[],
): GroupSettingPill | undefined {
    const funcs = [user_group_pill.create_item_from_group_name, user_pill.create_item_from_email];
    for (const func of funcs) {
        const item = func(text, current_items);
        if (item) {
            return item;
        }
    }
    return undefined;
}

export function get_text_from_item(item: GroupSettingPill): string {
    let text: string;
    switch (item.type) {
        case "user_group":
            text = user_group_pill.get_group_name_from_item(item);
            break;
        case "user":
            text = user_pill.get_email_from_item(item);
            break;
    }
    return text;
}

export function get_display_value_from_item(item: GroupSettingPill): string {
    if (item.type === "user_group") {
        return user_group_pill.display_pill(user_groups.get_user_group_from_id(item.group_id));
    }
    assert(item.type === "user");
    return user_pill.get_display_value_from_item(item);
}

export function generate_pill_html(item: GroupSettingPill): string {
    if (item.type === "user_group") {
        return render_input_pill({
            display_value: get_display_value_from_item(item),
            group_id: item.group_id,
        });
    }
    assert(item.type === "user");
    return user_pill.generate_pill_html(item);
}

export function create_pills($pill_container: JQuery): GroupSettingPillContainer {
    const pill_widget = input_pill.create<GroupSettingPill>({
        $container: $pill_container,
        create_item_from_text,
        get_text_from_item,
        get_display_value_from_item,
        generate_pill_html,
    });
    return pill_widget;
}
