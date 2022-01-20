import $ from "jquery";

import render_presence_row from "../templates/presence_row.hbs";
import render_presence_rows from "../templates/presence_rows.hbs";

import * as blueslip from "./blueslip";
import * as buddy_data from "./buddy_data";
import * as message_viewport from "./message_viewport";
import * as padded_widget from "./padded_widget";
import * as ui from "./ui";

class BuddyListConf {
    container_sel = "#user_presences";
    scroll_container_sel = "#buddy_list_wrapper";
    item_sel = "li.user_sidebar_entry";
    padding_sel = "#buddy_list_wrapper_padding";

    items_to_html(opts) {
        const html = render_presence_rows({presence_rows: opts.items});
        return html;
    }

    item_to_html(opts) {
        const html = render_presence_row(opts.item);
        return html;
    }

    get_li_from_key(opts) {
        const user_id = opts.key;
        const $container = $(this.container_sel);
        return $container.find(`${this.item_sel}[data-user-id='${CSS.escape(user_id)}']`);
    }

    get_key_from_li(opts) {
        return Number.parseInt(opts.$li.expectOne().attr("data-user-id"), 10);
    }

    get_data_from_keys(opts) {
        const keys = opts.keys;
        const data = buddy_data.get_items_for_people(keys);
        return data;
    }

    compare_function = buddy_data.compare_function;

    height_to_fill() {
        // Because the buddy list gets sized dynamically, we err on the side
        // of using the height of the entire viewport for deciding
        // how much content to render.  Even on tall monitors this should
        // still be a significant optimization for orgs with thousands of
        // users.
        const height = message_viewport.height();
        return height;
    }
}

export class BuddyList extends BuddyListConf {
    user_keys = [];

    populate(opts) {
        this.users_render_count = 0;
        this.$container.html("");

        // We rely on our caller to give us items
        // in already-sorted order.
        this.user_keys = opts.user_keys;

        this.fill_screen_with_content();
    }

    _render_more({chunk_size, begin, keys, section_sel}) {
        const end = begin + chunk_size;
        const more_keys = keys.slice(begin, end);

        if (more_keys.length === 0) {
            return 0;
        }

        const items = this.get_data_from_keys({
            keys: more_keys,
        });

        const html = this.items_to_html({
            items,
        });

        this.$section = $(section_sel);
        this.$section.append(html);

        // Invariant: more_keys.length >= items.length.
        // (Usually they're the same, but occasionally keys
        // won't return valid items.  Even though we don't
        // actually render these keys, we still "count" them
        // as rendered.
        return more_keys.length;
    }

    users_render_more(opts) {
        const render_count = this._render_more({
            chunk_size: opts.chunk_size,
            begin: this.users_render_count,
            keys: this.user_keys,
            section_sel: this.container_sel,
        });
        if (render_count > 0) {
            this.users_render_count += render_count;
            this.update_padding();
        }
    }

    get_items() {
        const $obj = this.$container.find(`${this.item_sel}`);
        return $obj.map((i, elem) => $(elem));
    }

    first_key() {
        return this.user_keys[0];
    }

    prev_key(key) {
        const i = this.user_keys.indexOf(key);

        if (i <= 0) {
            return undefined;
        }

        return this.user_keys[i - 1];
    }

    next_key(key) {
        const i = this.user_keys.indexOf(key);

        if (i < 0) {
            return undefined;
        }

        return this.user_keys[i + 1];
    }

    maybe_remove_key(opts) {
        this.maybe_remove_user_key(opts);
    }

    maybe_remove_user_key(opts) {
        const pos = this.user_keys.indexOf(opts.key);

        if (pos < 0) {
            return;
        }

        this.user_keys.splice(pos, 1);

        if (pos < this.users_render_count) {
            this.users_render_count -= 1;
            this._remove_key_and_update_padding(opts);
        }
    }

    _remove_key_and_update_padding(opts) {
        const $li = this.find_li({key: opts.key});
        $li.remove();
        this.update_padding();
    }

    _find_position({key, keys}) {
        let i;

        for (i = 0; i < keys.length; i += 1) {
            const list_key = keys[i];

            if (this.compare_function(key, list_key) < 0) {
                return i;
            }
        }

        return keys.length;
    }

    find_user_position(opts) {
        return this._find_position({
            key: opts.key,
            keys: this.user_keys,
        });
    }

    force_render(opts) {
        const pos = opts.pos;

        // Try to render a bit optimistically here.
        const cushion_size = 3;
        const chunk_size = pos + cushion_size - this.users_render_count;

        if (chunk_size <= 0) {
            blueslip.error("cannot show key at this position: " + pos);
        }

        this.users_render_more({
            chunk_size,
        });
    }

    find_li(opts) {
        const key = opts.key;

        // Try direct DOM lookup first for speed.
        let $li = this.get_li_from_key({
            key,
        });

        if ($li.length === 1) {
            return $li;
        }

        if (!opts.force_render) {
            // Most callers don't force us to render a list
            // item that wouldn't be on-screen anyway.
            return $li;
        }

        const pos = this.user_keys.indexOf(key);

        if (pos < 0) {
            // TODO: See ListCursor.get_row() for why this is
            //       a bit janky now.
            return [];
        }

        this.force_render({
            pos,
        });

        $li = this.get_li_from_key({
            key,
        });

        return $li;
    }

    insert_new_html(opts) {
        const new_key = opts.new_key;
        const html = opts.html;
        const pos = opts.pos;

        if (new_key === undefined) {
            if (pos === this.users_render_count) {
                this.users_render_count += 1;
                this.$container.append(html);
                this.update_padding();
            }
            return;
        }

        if (pos < this.users_render_count) {
            this.users_render_count += 1;
            const $li = this.find_li({key: new_key});
            $li.before(html);
            this.update_padding();
        }
    }

    insert_or_move(opts) {
        const key = opts.key;
        const item = opts.item;

        this.maybe_remove_key({key});

        const pos = this.find_user_position({
            key,
        });

        // Order is important here--get the new_key
        // before mutating our list.  An undefined value
        // corresponds to appending.
        const new_key = this.user_keys[pos];

        this.user_keys.splice(pos, 0, key);

        const html = this.item_to_html({item});
        this.insert_new_html({
            pos,
            html,
            new_key,
        });
    }

    fill_screen_with_content() {
        let height = this.height_to_fill();

        const elem = ui.get_scroll_element($(this.scroll_container_sel)).expectOne()[0];

        // Add a fudge factor.
        height += 10;

        while (this.users_render_count < this.user_keys.length) {
            const padding_height = $(this.padding_sel).height();
            const bottom_offset = elem.scrollHeight - elem.scrollTop - padding_height;

            if (bottom_offset > height) {
                break;
            }

            const chunk_size = 20;

            this.users_render_more({
                chunk_size,
            });
        }
    }

    // This is a bit of a hack to make sure we at least have
    // an empty list to start, before we get the initial payload.
    $container = $(this.container_sel);

    start_scroll_handler() {
        // We have our caller explicitly call this to make
        // sure everything's in place.
        const $scroll_container = ui.get_scroll_element($(this.scroll_container_sel));

        $scroll_container.on("scroll", () => {
            this.fill_screen_with_content();
        });
    }

    update_padding() {
        padded_widget.update_padding({
            shown_rows: this.users_render_count,
            total_rows: this.user_keys.length,
            content_sel: this.container_sel,
            padding_sel: this.padding_sel,
        });
    }
}

export const buddy_list = new BuddyList();
