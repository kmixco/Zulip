var topic_data = require('js/topic_data.js');

(function test_basics() {
    var stream_id = 55;

    topic_data.add_message({
        stream_id: stream_id,
        message_id: 101,
        topic_name: 'toPic1',
    });

    var history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['toPic1']);

    topic_data.add_message({
        stream_id: stream_id,
        message_id: 102,
        topic_name: 'Topic1',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['Topic1']);

    topic_data.add_message({
        stream_id: stream_id,
        message_id: 103,
        topic_name: 'topic2',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['topic2', 'Topic1']);

    // Removing first topic1 message has no effect.
    topic_data.remove_message({
        stream_id: stream_id,
        topic_name: 'toPic1',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['topic2', 'Topic1']);

    // Removing second topic1 message removes the topic.
    topic_data.remove_message({
        stream_id: stream_id,
        topic_name: 'Topic1',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['topic2']);

    // Test that duplicate remove does not crash us.
    topic_data.remove_message({
        stream_id: stream_id,
        topic_name: 'Topic1',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['topic2']);

    // get to 100% coverage for defensive code
    topic_data.remove_message({
        stream_id: 9999999,
    });
}());

(function test_server_history() {
    var stream_id = 66;

    topic_data.add_message({
        stream_id: stream_id,
        message_id: 501,
        topic_name: 'local',
    });

    function add_server_history() {
        topic_data.add_history(stream_id, [
            { name: 'local', max_id: 501 },
            { name: 'hist2', max_id: 31 },
            { name: 'hist1', max_id: 30 },
        ]);
    }

    add_server_history();
    var history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['local', 'hist2', 'hist1']);

    // If new activity comes in for historical messages,
    // they can bump to the front of the list.
    topic_data.add_message({
        stream_id: stream_id,
        message_id: 502,
        topic_name: 'hist1',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['hist1', 'local', 'hist2']);

    // server history is allowed to backdate hist1
    add_server_history();
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['local', 'hist2', 'hist1']);

    // Removing a local message removes the topic if we have
    // our counts right.
    topic_data.remove_message({
        stream_id: stream_id,
        topic_name: 'local',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['hist2', 'hist1']);

    // We can try to remove a historical message, but it should
    // have no effect.
    topic_data.remove_message({
        stream_id: stream_id,
        topic_name: 'hist2',
    });
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['hist2', 'hist1']);

    // If we call back to the server for history, the
    // effect is always additive.  We may decide to prune old
    // topics in the future, if they dropped off due to renames,
    // but that is probably an edge case we can ignore for now.
    topic_data.add_history(stream_id, [
        { name: 'hist2', max_id: 931 },
        { name: 'hist3', max_id: 5 },
    ]);
    history = topic_data.get_recent_names(stream_id);
    assert.deepEqual(history, ['hist2', 'hist1', 'hist3']);
}());



