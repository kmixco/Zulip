import {strict as assert} from "assert";

import type {ElementHandle, Page} from "puppeteer";

import common from "../puppeteer_lib/common";

async function user_checkbox(page: Page, name: string): Promise<string> {
    const user_id = await common.get_user_id_from_name(page, name);
    return `#user_checkbox_${CSS.escape(user_id.toString())}`;
}

async function wait_for_checked(page: Page, user_name: string, is_checked: boolean): Promise<void> {
    const selector = await user_checkbox(page, user_name);
    await page.waitForFunction(
        (selector: string, is_checked: boolean) =>
            $(selector).find("input").prop("checked") === is_checked,
        {},
        selector,
        is_checked,
    );
}

async function add_user_to_stream(page: Page, name: string): Promise<void> {
    const user_id = await common.get_user_id_from_name(page, name);
    await page.evaluate(
        (user_id: Number) => zulip_test.add_user_id_to_new_stream(user_id),
        user_id,
    );
    await wait_for_checked(page, name, true);
}

async function stream_name_error(page: Page): Promise<string> {
    await page.waitForSelector("#stream_name_error", {visible: true});
    return await common.get_text_from_selector(page, "#stream_name_error");
}

async function open_streams_modal(page: Page): Promise<void> {
    const all_streams_selector = "#add-stream-link";
    await page.waitForSelector(all_streams_selector, {visible: true});
    await page.click(all_streams_selector);

    await page.waitForSelector("#subscription_overlay.new-style", {visible: true});
    const url = await common.page_url_with_fragment(page);
    assert.ok(url.includes("#streams/all"));
}

async function test_subscription_button(page: Page): Promise<void> {
    const stream_selector = "[data-stream-name='Venice']";
    const button_selector = `${stream_selector} .sub_unsub_button`;
    const subscribed_selector = `${button_selector}.checked`;
    const unsubscribed_selector = `${button_selector}:not(.checked)`;

    async function subscribed(): Promise<ElementHandle | null> {
        return await page.waitForSelector(subscribed_selector, {visible: true});
    }

    async function unsubscribed(): Promise<ElementHandle | null> {
        return await page.waitForSelector(unsubscribed_selector, {visible: true});
    }

    // Make sure that Venice is even in our list of streams.
    await page.waitForSelector(stream_selector, {visible: true});
    await page.waitForSelector(button_selector, {visible: true});

    // Note that we intentionally re-find the button after each click, since
    // the live-update code may replace the whole row.
    let button;

    // We assume Venice is already subscribed, so the first line here
    // should happen immediately.
    button = await subscribed();
    await button!.click();
    button = await unsubscribed();
    await button!.click();
    button = await subscribed();
    await button!.click();
    button = await unsubscribed();
    await button!.click();
    button = await subscribed();
}

async function click_create_new_stream(page: Page): Promise<void> {
    const desdemona_checkbox = await user_checkbox(page, "desdemona");
    await page.click("#add_new_subscription .create_stream_button");
    await page.waitForSelector(desdemona_checkbox, {visible: true});
}

async function clear_ot_filter_with_backspace(page: Page): Promise<void> {
    await page.click(".add-user-list-filter");
    await page.keyboard.press("Backspace");
    await page.keyboard.press("Backspace");
}

async function test_user_filter_ui(page: Page): Promise<void> {
    await page.waitForSelector("form#stream_creation_form", {visible: true});
    // Desdemona should be checked by default
    await wait_for_checked(page, "desdemona", true);

    await add_user_to_stream(page, "cordelia");
    await add_user_to_stream(page, "othello");

    const cordelia_checkbox = await user_checkbox(page, "cordelia");
    const desdemona_checkbox = await user_checkbox(page, "desdemona");
    const othello_checkbox = await user_checkbox(page, "othello");

    await page.type(`form#stream_creation_form [name="user_list_filter"]`, "ot", {delay: 100});
    await page.waitForSelector("#user-checkboxes", {visible: true});
    // Wait until filtering is completed.
    await page.waitForFunction(
        () => document.querySelectorAll("#user-checkboxes label").length === 1,
    );

    await page.waitForSelector(cordelia_checkbox, {hidden: true});
    await page.waitForSelector(desdemona_checkbox, {hidden: true});
    await page.waitForSelector(othello_checkbox, {visible: true});

    // Test unset all with filter
    await page.click(".subs_unset_all_users");
    await wait_for_checked(page, "othello", false);

    // Test check all with filter
    await page.click(".subs_set_all_users");
    await wait_for_checked(page, "othello", true);

    // And unset othello again.
    await page.click(".subs_unset_all_users");
    await wait_for_checked(page, "othello", false);

    // Clear the filter.
    await clear_ot_filter_with_backspace(page);

    await page.waitForSelector(cordelia_checkbox, {visible: true});
    await page.waitForSelector(desdemona_checkbox, {visible: true});
    await page.waitForSelector(othello_checkbox, {visible: true});

    // Make sure desdemona and cordelia are still set.
    await wait_for_checked(page, "cordelia", true);
    await wait_for_checked(page, "desdemona", true);

    // Test unset all
    await page.click(".subs_unset_all_users");
    await wait_for_checked(page, "cordelia", false);
    await wait_for_checked(page, "desdemona", false);
    await wait_for_checked(page, "othello", false);

    // Test check all
    await page.click(".subs_set_all_users");
    await wait_for_checked(page, "cordelia", true);
    await wait_for_checked(page, "desdemona", true);
    await wait_for_checked(page, "othello", true);
}

async function create_stream(page: Page): Promise<void> {
    await page.waitForXPath('//*[text()="Create stream"]', {visible: true});
    await common.fill_form(page, "form#stream_creation_form", {
        stream_name: "Puppeteer",
        stream_description: "Everything Puppeteer",
    });
    await add_user_to_stream(page, "cordelia");
    await add_user_to_stream(page, "desdemona");
    await page.click("form#stream_creation_form button.button.sea-green");
    await page.waitForFunction(() => $(".stream-name").is(':contains("Puppeteer")'));
    const stream_name = await common.get_text_from_selector(
        page,
        ".stream-header .stream-name .sub-stream-name",
    );
    const stream_description = await common.get_text_from_selector(
        page,
        ".stream-description .sub-stream-description",
    );
    const subscriber_count_selector = "[data-stream-name='Puppeteer'] .subscriber-count";
    assert.strictEqual(stream_name, "Puppeteer");
    assert.strictEqual(stream_description, "Everything Puppeteer");

    // Assert subscriber count becomes 3 (cordelia, desdemona, othello)
    await page.waitForFunction(
        (subscriber_count_selector: string) => $(subscriber_count_selector).text().trim() === "3",
        {},
        subscriber_count_selector,
    );
}

async function test_streams_with_empty_names_cannot_be_created(page: Page): Promise<void> {
    await page.click("#add_new_subscription .create_stream_button");
    await page.waitForSelector("form#stream_creation_form", {visible: true});
    await common.fill_form(page, "form#stream_creation_form", {stream_name: "  "});
    await page.click("form#stream_creation_form button.button.sea-green");
    assert.strictEqual(await stream_name_error(page), "A stream needs to have a name");
}

async function test_streams_with_duplicate_names_cannot_be_created(page: Page): Promise<void> {
    await common.fill_form(page, "form#stream_creation_form", {stream_name: "Puppeteer"});
    await page.click("form#stream_creation_form button.button.sea-green");
    assert.strictEqual(await stream_name_error(page), "A stream with this name already exists");

    const cancel_button_selector = "form#stream_creation_form button.button.white";
    await page.click(cancel_button_selector);
}

async function test_stream_creation(page: Page): Promise<void> {
    await click_create_new_stream(page);
    await test_user_filter_ui(page);
    await create_stream(page);
    await test_streams_with_empty_names_cannot_be_created(page);
    await test_streams_with_duplicate_names_cannot_be_created(page);
}

async function test_streams_search_feature(page: Page): Promise<void> {
    assert.strictEqual(await common.get_text_from_selector(page, "#search_stream_name"), "");
    const hidden_streams_selector = ".stream-row.notdisplayed .stream-name";
    assert.strictEqual(
        await common.get_text_from_selector(
            page,
            '.stream-row[data-stream-name="Verona"] .stream-name',
        ),
        "Verona",
    );
    assert.ok(
        !(await common.get_text_from_selector(page, hidden_streams_selector)).includes("Verona"),
        "#Verona is hidden",
    );

    await page.type('#stream_filter input[type="text"]', "Puppeteer");
    await page.waitForSelector(".stream-row[data-stream-name='core team']", {hidden: true});
    assert.strictEqual(
        await common.get_text_from_selector(page, ".stream-row:not(.notdisplayed) .stream-name"),
        "Puppeteer",
    );
    assert.ok(
        (await common.get_text_from_selector(page, hidden_streams_selector)).includes("Verona"),
        "#Verona is not hidden",
    );
    assert.ok(
        !(await common.get_text_from_selector(page, hidden_streams_selector)).includes("Puppeteer"),
        "Puppeteer is hidden after searching.",
    );
}

async function subscriptions_tests(page: Page): Promise<void> {
    await common.log_in(page);
    await open_streams_modal(page);
    await test_subscription_button(page);
    await test_stream_creation(page);
    await test_streams_search_feature(page);
}

common.run_test(subscriptions_tests);
