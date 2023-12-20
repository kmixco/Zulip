import $ from "jquery";

import * as util from "./util";

const list_selectors = [
    "#stream_filters",
    "#left-sidebar-navigation-list",
    "#buddy-list-users-matching-view",
    "#send_later_options",
];

export function inside_list(e: JQuery.KeyDownEvent | JQuery.KeyPressEvent): boolean {
    const $target = $(e.target);
    const in_list = $target.closest(util.format_array_as_list(list_selectors)).length > 0;
    return in_list;
}

export function go_down(e: JQuery.KeyDownEvent | JQuery.KeyPressEvent): void {
    const $target = $(e.target);
    $target.closest("li").next().find("a").trigger("focus");
}

export function go_up(e: JQuery.KeyDownEvent | JQuery.KeyPressEvent): void {
    const $target = $(e.target);
    $target.closest("li").prev().find("a").trigger("focus");
}
