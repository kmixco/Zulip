import {renderGrid} from "@giphy/js-components";
import {GiphyFetch} from "@giphy/js-fetch-api";
import $ from "jquery";
import _ from "lodash";

import render_giphy_picker from "../templates/giphy_picker.hbs";
import render_giphy_picker_mobile from "../templates/giphy_picker_mobile.hbs";

import * as compose_ui from "./compose_ui";
import {media_breakpoints_num} from "./css_variables";
import {page_params} from "./page_params";
import * as popovers from "./popovers";
import * as rows from "./rows";
import * as ui_util from "./ui_util";

const giphy_fetch = new GiphyFetch(page_params.giphy_api_key);
let search_term = "";
let gifs_grid;
let active_popover_element;

// Only used if popover called from edit message, otherwise it is `undefined`.
let edit_message_id;

export function is_popped_from_edit_messsage() {
    return active_popover_element && edit_message_id !== undefined;
}

export function focus_current_edit_message() {
    $(`#edit_form_${CSS.escape(edit_message_id)} .message_edit_content`).trigger("focus");
}

// Approximate width and height of
// giphy popover as computed by chrome
// + 25px;
const APPROX_HEIGHT = 350;
const APPROX_WIDTH = 300;

function fetchGifs(offset) {
    const config = {
        offset,
        limit: 25,
        // Default rating to 'g' until we can make this configurable.
        rating: "g",
        // We don't pass random_id here, for privacy reasons.
    };
    if (search_term === "") {
        // Get the trending gifs by default.
        return giphy_fetch.trending(config);
    }
    return giphy_fetch.search(search_term, config);
}

function renderGIPHYGrid(targetEl) {
    const render = () =>
        // See https://github.com/Giphy/giphy-js/blob/master/packages/components/README.md#grid
        // for detailed documentation.
        renderGrid(
            {
                width: 300,
                fetchGifs,
                columns: 3,
                gutter: 6,
                noLink: true,
                // Hide the creator attribution that appears over a
                // GIF; nice in principle but too distracting.
                hideAttribution: true,
                onGifClick: (props) => {
                    let textarea = $("#compose-textarea");
                    if (edit_message_id !== undefined) {
                        textarea = $(
                            `#edit_form_${CSS.escape(edit_message_id)} .message_edit_content`,
                        );
                    }

                    compose_ui.insert_syntax_and_focus(
                        `[](${props.images.downsized_medium.url})`,
                        textarea,
                    );
                    hide_giphy_popover();
                },
                onGifVisible: (gif, e) => {
                    // Set tabindex for all the GIFs that
                    // are visible to the user. This allows
                    // user to navigate the GIFs using tab.
                    // TODO: Remove this after https://github.com/Giphy/giphy-js/issues/174
                    // is closed.
                    e.target.tabIndex = 0;
                },
            },
            targetEl,
        );

    // Limit the rate at which we do queries to the GIPHY API to
    // one per 300ms, in line with animation timing, basically to avoid
    // content appearing while the user is typing.
    const resizeRender = _.throttle(render, 300);
    window.addEventListener("resize", resizeRender, false);
    const remove = render();
    return {
        remove: () => {
            remove();
            window.removeEventListener("resize", resizeRender, false);
        },
    };
}

function update_grid_with_search_term() {
    if (!gifs_grid) {
        return;
    }

    const search_elem = $("#giphy-search-query");
    // GIPHY popover may have been hidden by the
    // time this function is called.
    if (search_elem.length) {
        search_term = search_elem[0].value;
        gifs_grid.remove();
        gifs_grid = renderGIPHYGrid($("#giphy_grid_in_popover .giphy-content")[0]);
        return;
    }

    // Set to undefined to stop searching.
    gifs_grid = undefined;
}

export function hide_giphy_popover() {
    // Returns `true` if the popover was open.
    if (active_popover_element) {
        // We need to destroy the popover because when
        // we hide it, bootstrap popover
        // library removes `giphy-content` element
        // as part of cleaning up everything inside
        // `popover-content`, so we need to reinitialize
        // the popover by destroying it.
        active_popover_element.popover("destroy");
        active_popover_element = undefined;
        edit_message_id = undefined;
        return true;
    }
    return false;
}

function get_popover_content() {
    if (window.innerWidth <= media_breakpoints_num.md) {
        // Show as modal in the center for small screens.
        return render_giphy_picker_mobile();
    }
    return render_giphy_picker();
}

function get_popover_placement() {
    let placement = popovers.compute_placement(
        active_popover_element,
        APPROX_HEIGHT,
        APPROX_WIDTH,
        true,
    );

    if (placement === "viewport_center") {
        // For legacy reasons `compute_placement` actually can
        // return `viewport_center` which used to place popover in
        // the center of the screen, but bootstrap doesn't actually
        // support that and we already handle it on small screen sizes
        // by placing it in center using `popover-flex`.
        placement = "left";
    }

    return placement;
}

export function initialize() {
    $("body").on("keydown", ".giphy-gif", ui_util.convert_enter_to_click);
    $("body").on("keydown", ".compose_giphy_logo", ui_util.convert_enter_to_click);

    $("body").on("click", "#giphy_search_clear", (e) => {
        e.stopPropagation();
        $("#giphy-search-query").val("");
        update_grid_with_search_term();
    });

    $("body").on("click", ".compose_giphy_logo", (e) => {
        e.preventDefault();
        e.stopPropagation();

        if (active_popover_element && $.contains(active_popover_element.get()[0], e.target)) {
            // Hide giphy popover if already active.
            hide_giphy_popover();
            return;
        }
        popovers.hide_all();
        const $elt = $(e.target);
        if ($elt.parents(".message_edit_form").length === 1) {
            // Store message id in global variable edit_message_id so that
            // its value can be further used to correctly find the message textarea element.
            edit_message_id = rows.id($elt.parents(".message_row"));
        } else {
            edit_message_id = undefined;
        }

        active_popover_element = $elt.closest("#compose_box_giphy_grid");
        active_popover_element.popover({
            animation: true,
            placement: get_popover_placement(),
            html: true,
            trigger: "manual",
            template: get_popover_content(),
        });

        active_popover_element.popover("show");
        // Allow simplebar to render, then fetch and
        // render GIFs. otherwise simplebar replaces
        // the `.gipihy-content` element when trying
        // to wrap it and hence, our jquery reference
        // to `.giphy-content` is lost. Thus, no GIF
        // is rendered.
        setTimeout(() => {
            gifs_grid = renderGIPHYGrid($("#giphy_grid_in_popover .giphy-content")[0]);
        }, 0);

        $("body").on(
            "keyup",
            "#giphy-search-query",
            // Use debounce to create a 300ms interval between
            // every search. This makes the UX of searching pleasant
            // by allowing user to finish typing before search
            // is executed.
            _.debounce(update_grid_with_search_term, 300),
        );

        $(document).one("compose_canceled.zulip compose_finished.zulip", () => {
            hide_giphy_popover();
        });

        // Focus on search box by default.
        // This is specially helpful for users
        // navigating via keyboard.
        $("#giphy-search-query").trigger("focus");
    });
}
