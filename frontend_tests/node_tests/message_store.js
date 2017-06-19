add_dependencies({
    people: 'js/people.js',
    util: 'js/util.js',
    pm_conversations: 'js/pm_conversations.js',
});

var noop = function () {};
var with_overrides = global.with_overrides;
var people = global.people;

set_global('alert_words', {
    process_message: noop,
});

set_global('stream_data' , {
    process_message_for_recent_topics: noop,
});

set_global('recent_senders', {
    process_message_for_senders: noop,
});

set_global('page_params', {
    realm_allow_message_editing: true,
    is_admin: true,
});

set_global('blueslip', {
    error: noop,
});

var me = {
    email: 'me@example.com',
    user_id: 101,
    full_name: 'Me Myself',
};

var alice = {
    email: 'alice@example.com',
    user_id: 102,
    full_name: 'Alice',
};

var bob = {
    email: 'bob@example.com',
    user_id: 103,
    full_name: 'Bob',
};

var cindy = {
    email: 'cindy@example.com',
    user_id: 104,
    full_name: 'Cindy',
};

people.add_in_realm(me);
people.add_in_realm(alice);
people.add_in_realm(bob);
people.add_in_realm(cindy);

global.people.initialize_current_user(me.user_id);

global.util.execute_early = noop;

var message_store = require('js/message_store.js');

(function test_insert_recent_private_message() {
    message_store.insert_recent_private_message('1', 1001);
    message_store.insert_recent_private_message('2', 2001);
    message_store.insert_recent_private_message('1', 3001);

    // try to backdate user1's timestamp
    message_store.insert_recent_private_message('1', 555);

    assert.deepEqual(message_store.recent_private_messages, [
        {user_ids_string: '1', timestamp: 3001},
        {user_ids_string: '2', timestamp: 2001},
    ]);
}());

(function test_add_message_metadata() {
    var message = {
        sender_email: 'me@example.com',
        sender_id: me.user_id,
        type: 'private',
        display_recipient: [me, bob, cindy],
        flags: ['has_alert_word'],
        id: 2067,
    };
    message_store.add_message_metadata(message);

    assert.equal(message.is_private, true);
    assert.equal(message.reply_to, 'bob@example.com,cindy@example.com');
    assert.equal(message.to_user_ids, '103,104');
    assert.equal(message.display_reply_to, 'Bob, Cindy');
    assert.equal(message.alerted, true);
    assert.equal(message.is_me_message, false);

    var retrieved_message = message_store.get(2067);
    assert.equal(retrieved_message, message);

    // access cached previous message, and test match subject/content
    message = {
        id: 2067,
        match_subject: "subject foo",
        match_content: "bar content",
    };
    message = message_store.add_message_metadata(message);

    assert.equal(message.reply_to, 'bob@example.com,cindy@example.com');
    assert.equal(message.to_user_ids, '103,104');
    assert.equal(message.display_reply_to, 'Bob, Cindy');
    assert.equal(message.match_subject, 'subject foo');
    assert.equal(message.match_content, 'bar content');

    message = {
        sender_email: 'me@example.com',
        sender_id: me.user_id,
        type: 'stream',
        display_recipient: [me, cindy],
        stream: 'Zoolippy',
        topic: 'cool thing',
        subject: 'the_subject',
        id: 2068,
    };

    // test stream properties
    with_overrides(function (override) {
        override('compose.empty_topic_placeholder', function () {
            return 'the_subject';
        });
        global.with_stub(function (stub) {
            set_global('composebox_typeahead', {add_topic: stub.f});
            message_store.add_message_metadata(message);
            var typeahead_added = stub.get_args('stream', 'subject');
            assert.deepEqual(typeahead_added.stream, [me, cindy]);
            assert.equal(message.subject, typeahead_added.subject);
        });

        assert.equal(message.always_visible_topic_edit, true);
        assert.equal(message.on_hover_topic_edit, false);
        assert.deepEqual(message.stream, [me, cindy]);
        assert.equal(message.reply_to, 'me@example.com');
        assert.deepEqual(message.flags, []);
        assert.equal(message.alerted, false);

        override('compose.empty_topic_placeholder', function () {
            return 'not_the_subject';
        });

        message = {
            sender_id: me.user_id,
            type: 'stream',
            id: 2069,
            display_recipient: [me],
            sender_email: 'me@example.org',
        };
        message_store.add_message_metadata(message);

        assert.equal(message.always_visible_topic_edit, false);
        assert.equal(message.on_hover_topic_edit, true);
    });

    page_params.realm_allow_message_editing = false;
    message = {
        sender_id: me.user_id,
        type: 'stream',
        id: 2070,
        display_recipient: [me],
        sender_email: 'me@example.org',
    };
    message_store.add_message_metadata(message);
    assert.equal(message.always_visible_topic_edit, false);
    assert.equal(message.on_hover_topic_edit, false);
}());
