set_global('$', global.make_zjquery());
set_global('people', {});
set_global('markdown', {});
set_global('local_message', {
    now: () => "timestamp",
});
set_global('page_params', {});

zrequire('echo');
zrequire('util');

let disparities = [];
let messages_to_rerender = [];

set_global('sent_messages', {
    mark_disparity: (local_id) => {
        disparities.push(local_id);
    },
});

set_global('message_store', {
    update_booleans: () => {},
});

set_global('alert_words', {
    process_message: () => {},
});

set_global('home_msg_list', {
    view: {
        rerender_messages: (msgs) => {
            messages_to_rerender = msgs;
        },
    },
});

set_global('message_list', {});

set_global('current_msg_list', '');

run_test('process_from_server for un-echoed messages', () => {
    const waiting_for_ack = {};
    const server_messages = [
        {
            local_id: 100.1,
        },
    ];
    echo._patch_waiting_for_awk(waiting_for_ack);
    const non_echo_messages = echo.process_from_server(server_messages);
    assert.deepEqual(non_echo_messages, server_messages);
});

run_test('process_from_server for differently rendered messages', () => {
    // Test that we update all the booleans and the content of the message
    // in local echo.
    const old_value = 'old_value';
    const new_value = 'new_value';
    const waiting_for_ack = {
        100.1: {
            content: "<p>A client rendered message</p>",
            timestamp: old_value,
            is_me_message: old_value,
            submessages: old_value,
            subject_links: old_value,
        },
    };
    const server_messages = [
        {
            local_id: 100.1,
            content: "<p>A server rendered message</p>",
            timestamp: new_value,
            is_me_message: new_value,
            submessages: new_value,
            subject_links: new_value,
        },
    ];
    echo._patch_waiting_for_awk(waiting_for_ack);
    messages_to_rerender = [];
    disparities = [];
    const non_echo_messages = echo.process_from_server(server_messages);
    assert.deepEqual(non_echo_messages, []);
    assert.equal(disparities.length, 1);
    assert.deepEqual(messages_to_rerender, [{
        content: server_messages[0].content,
        timestamp: new_value,
        is_me_message: new_value,
        submessages: new_value,
        subject_links: new_value,
    }]);
});

run_test('insert_local_message', () => {
    const local_id = 1;
    people.my_current_email = () => "iago@zulip.com";
    people.my_full_name = () => "Iago";

    let apply_markdown_called = false;
    let add_topic_links_called = false;
    let insert_message_called = false;

    markdown.apply_markdown = () => {
        apply_markdown_called = true;
    };

    markdown.add_topic_links = () => {
        add_topic_links_called = true;
    };

    local_message.insert_message = (message) => {
        assert.equal(message.display_recipient, "general");
        assert.equal(message.timestamp, "timestamp");
        assert.equal(message.sender_email, "iago@zulip.com");
        assert.equal(message.sender_full_name, "Iago");
        assert.equal(message.sender_id, 123);
        insert_message_called = true;
    };

    let message_request = {
        type: "stream",
        stream: "general",
        sender_email: "iago@zulip.com",
        sender_full_name: "Iago",
        sender_id: 123,
    };
    echo.insert_local_message(message_request, local_id);

    assert(apply_markdown_called);
    assert(add_topic_links_called);
    assert(insert_message_called);

    add_topic_links_called = false;
    apply_markdown_called = false;
    insert_message_called = false;

    people.get_by_email = () => {};

    local_message.insert_message = (message) => {
        assert.equal(message.display_recipient.length, 2);
        insert_message_called = true;
    };

    message_request = {
        private_message_recipient: "cordelia@zulip.com,hamlet@zulip.com",
        type: "private",
        sender_email: "iago@zulip.com",
        sender_full_name: "Iago",
        sender_id: 123,
    };
    echo.insert_local_message(message_request, local_id);
    assert(add_topic_links_called);
    assert(apply_markdown_called);
    assert(insert_message_called);

});
