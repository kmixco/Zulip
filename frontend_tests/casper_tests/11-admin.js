var common = require('../casper_lib/common.js').common;
var test_credentials = require('../casper_lib/test_credentials.js').test_credentials;

common.start_and_log_in();

casper.then(function () {
    casper.test.info('Administration page');
    casper.click('a[href^="#administration"]');
    casper.test.assertUrlMatch(/^http:\/\/[^\/]+\/#administration/, 'URL suggests we are on administration page');
    casper.test.assertExists('#administration.tab-pane.active', 'Administration page is active');
});

// Test user deactivation and reactivation
casper.waitForSelector('.user_row[id="user_cordelia@zulip.com"]', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_cordelia@zulip.com"]', 'Deactivate');
    casper.click('.user_row[id="user_cordelia@zulip.com"] .deactivate');
    casper.test.assertTextExists('Deactivate cordelia@zulip.com', 'Deactivate modal has right user');
    casper.test.assertTextExists('Deactivate now', 'Deactivate now button available');
    casper.click('#do_deactivate_user_button');
});

casper.waitForSelector('.user_row[id="user_cordelia@zulip.com"].deactivated_user', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_cordelia@zulip.com"]', 'Reactivate');
    casper.click('.user_row[id="user_cordelia@zulip.com"] .reactivate');
});

casper.waitForSelector('.user_row[id="user_cordelia@zulip.com"]:not(.deactivated_user)', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_cordelia@zulip.com"]', 'Deactivate');
});

// Test Deactivated users section of admin page
casper.waitForSelector('.user_row[id="user_cordelia@zulip.com"]', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_cordelia@zulip.com"]', 'Deactivate');
    casper.click('.user_row[id="user_cordelia@zulip.com"] .deactivate');
    casper.test.assertTextExists('Deactivate cordelia@zulip.com', 'Deactivate modal has right user');
    casper.test.assertTextExists('Deactivate now', 'Deactivate now button available');
    casper.click('#do_deactivate_user_button');
});

casper.then(function () {
    // Leave the page and return
    casper.click('#settings-dropdown');
    casper.click('a[href^="#subscriptions"]');
    casper.click('#settings-dropdown');
    casper.click('a[href^="#administration"]');

    casper.waitForSelector('.user_row[id="user_cordelia@zulip.com"]', function () {
        casper.test.assertSelectorHasText('#admin_deactivated_users_table .user_row[id="user_cordelia@zulip.com"]', 'Reactivate');
        casper.click('#admin_deactivated_users_table .user_row[id="user_cordelia@zulip.com"] .reactivate');
    });

    casper.waitForSelector('#admin_deactivated_users_table .user_row[id="user_cordelia@zulip.com"]:not(.deactivated_user)', function () {
        casper.test.assertSelectorHasText('#admin_deactivated_users_table .user_row[id="user_cordelia@zulip.com"]', 'Deactivate');
    });
});

// Test bot deactivation and reactivation
casper.waitForSelector('.user_row[id="user_new-user-bot@zulip.com"]', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_new-user-bot@zulip.com"]', 'Deactivate');
    casper.click('.user_row[id="user_new-user-bot@zulip.com"] .deactivate');
});

casper.waitForSelector('.user_row[id="user_new-user-bot@zulip.com"].deactivated_user', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_new-user-bot@zulip.com"]', 'Reactivate');
    casper.click('.user_row[id="user_new-user-bot@zulip.com"] .reactivate');
});
casper.waitForSelector('.user_row[id="user_new-user-bot@zulip.com"]:not(.deactivated_user)', function () {
    casper.test.assertSelectorHasText('.user_row[id="user_new-user-bot@zulip.com"]', 'Deactivate');
});

// TODO: Test stream deletion

common.then_log_out();

casper.run(function () {
    casper.test.done();
});
