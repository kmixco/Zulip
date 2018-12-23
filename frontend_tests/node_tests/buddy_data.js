const _page_params = {};

set_global('page_params', _page_params);
zrequire('people');
zrequire('presence');
zrequire('util');
zrequire('user_status');
zrequire('buddy_data');
zrequire('user_status');

// The buddy_data module is mostly tested indirectly through
// activity.js, but we should feel free to add direct tests
// here.

const selma = {
    user_id: 1000,
    full_name: 'Human Selma',
    email: 'selma@example.com',
};

const me = {
    user_id: 1001,
    full_name: 'Human Myself',
    email: 'self@example.com',
};

const bot = {
    user_id: 55555,
    full_name: 'Red Herring Bot',
    email: 'bot@example.com',
    is_bot: true,
};

function make_people() {
    _.each(_.range(1002, 2000), (i) => {
        const person = {
            user_id: i,
            full_name: `Human ${i}`,
            email: `person${i}@example.com`,
        };
        people.add_in_realm(person);
    });

    people.add_in_realm(bot);
    people.add_in_realm(selma);
    people.add_in_realm(me);

    people.initialize_current_user(me.user_id);
}


function activate_people() {
    const server_time = 9999;
    const info = {
        website: {
            status: "active",
            timestamp: server_time,
        },
    };

    // Make 400 of the users active
    presence.set_info_for_user(selma.user_id, info, server_time);
    presence.set_info_for_user(me.user_id, info, server_time);

    _.each(_.range(1000, 1400), (user_id) => {
        presence.set_info_for_user(user_id, info, server_time);
    });


    // And then 300 not active
    _.each(_.range(1400, 1700), (user_id) => {
        presence.set_info_for_user(user_id, {}, server_time);
    });
}


make_people();
activate_people();

run_test('buddy_status', () => {
    assert.equal(buddy_data.buddy_status(selma.user_id), 'active');
    user_status.set_away(selma.user_id);
    assert.equal(buddy_data.buddy_status(selma.user_id), 'away_them');
    user_status.revoke_away(selma.user_id);
    assert.equal(buddy_data.buddy_status(selma.user_id), 'active');

    assert.equal(buddy_data.buddy_status(me.user_id), 'active');
    user_status.set_away(me.user_id);
    assert.equal(buddy_data.buddy_status(me.user_id), 'away_me');
    user_status.revoke_away(me.user_id);
    assert.equal(buddy_data.buddy_status(me.user_id), 'active');
});

run_test('simple search', () => {
    const user_ids = buddy_data.get_filtered_and_sorted_user_ids('sel');

    assert.deepEqual(user_ids, [selma.user_id]);
});

run_test('bulk_data_hacks', () => {
    var user_ids;

    // Even though we have 1000 users, we only get the 400 active
    // users.  This is a consequence of buddy_data.maybe_shrink_list.
    user_ids = buddy_data.get_filtered_and_sorted_user_ids();
    assert.equal(user_ids.length, 400);

    user_ids = buddy_data.get_filtered_and_sorted_user_ids('');
    assert.equal(user_ids.length, 400);

    // We don't match on "so", because it's not at the start of a
    // word in the name/email.
    user_ids = buddy_data.get_filtered_and_sorted_user_ids('so');
    assert.equal(user_ids.length, 0);

    // We match on "h" for the first name, and the result limit
    // is relaxed for searches.  (We exclude "me", though.)
    user_ids = buddy_data.get_filtered_and_sorted_user_ids('h');
    assert.equal(user_ids.length, 999);

    // We match on "p" for the email.
    user_ids = buddy_data.get_filtered_and_sorted_user_ids('p');
    assert.equal(user_ids.length, 998);


    // Make our shrink limit higher, and go back to an empty search.
    // We won't get all 1000 users, just the present ones.
    buddy_data.max_size_before_shrinking = 50000;

    user_ids = buddy_data.get_filtered_and_sorted_user_ids('');
    assert.equal(user_ids.length, 700);
});

run_test('level', () => {
    presence.presence_info = {};
    assert.equal(buddy_data.level(me.user_id), 0);
    assert.equal(buddy_data.level(selma.user_id), 3);

    const server_time = 9999;
    const info = {
        website: {
            status: "active",
            timestamp: server_time,
        },
    };
    presence.set_info_for_user(me.user_id, info, server_time);
    presence.set_info_for_user(selma.user_id, info, server_time);

    assert.equal(buddy_data.level(me.user_id), 0);
    assert.equal(buddy_data.level(selma.user_id), 1);

    user_status.set_away(me.user_id);
    user_status.set_away(selma.user_id);

    // Selma gets demoted to level 3, but "me"
    // stays in level 0.
    assert.equal(buddy_data.level(me.user_id), 0);
    assert.equal(buddy_data.level(selma.user_id), 3);
});
