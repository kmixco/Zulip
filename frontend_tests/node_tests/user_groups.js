set_global('blueslip', global.make_zblueslip());
set_global('page_params', {});

zrequire('user_groups');

run_test('user_groups', () => {
    const students = {
        name: 'Students',
        id: 0,
        members: [1, 2],
    };

    const non_active_grp = {
        name: 'Non_Active',
        description: 'deactivated group',
        id: 3,
        members: [1, 2, 3],
    };

    global.page_params.realm_user_groups = [students];
    global.page_params.realm_non_active_user_groups = [non_active_grp];

    user_groups.initialize();
    assert.equal(user_groups.get_user_group_from_id(students.id), students);
    assert.equal(user_groups.get_active_user_group_from_id(students.id), students);

    assert.equal(user_groups.get_user_group_from_id(non_active_grp.id), non_active_grp);

    const admins = {
        name: 'Admins',
        description: 'foo',
        id: 1,
        members: [3],
    };
    const all = {
        name: 'Everyone',
        id: 2,
        members: [1, 2, 3],
    };

    user_groups.add_in_realm(admins);
    assert.equal(user_groups.get_user_group_from_id(admins.id), admins);
    assert.equal(user_groups.get_active_user_group_from_id(admins.id), admins);

    const update_name_event = {
        group_id: admins.id,
        data: {
            name: "new admins",
        },
    };
    user_groups.update(update_name_event);
    assert.equal(user_groups.get_user_group_from_id(admins.id).name, "new admins");

    const update_des_event = {
        group_id: admins.id,
        data: {
            description: "administer",
        },
    };
    user_groups.update(update_des_event);
    assert.equal(user_groups.get_user_group_from_id(admins.id).description, "administer");

    blueslip.set_test_data('error', 'Unknown group_id in get_user_group_from_id: ' + all.id);
    assert.equal(user_groups.get_user_group_from_id(all.id), undefined);
    assert.equal(blueslip.get_test_logs('error').length, 1);
    blueslip.clear_test_data();

    user_groups.remove(students);

    blueslip.set_test_data('error', 'Unknown group_id in get_active_user_group_from_id: ' + students.id);
    assert.equal(user_groups.get_user_group_from_id(students.id), students);
    assert.equal(user_groups.is_active_user_group(students), false);
    assert.equal(user_groups.get_active_user_group_from_id(students.id), undefined);
    assert.equal(blueslip.get_test_logs('error').length, 1);
    blueslip.clear_test_data();
    let active_user_groups_array = user_groups.get_realm_user_groups();
    assert.equal(active_user_groups_array.length, 1);

    assert.equal(user_groups.get_user_group_from_name(all.name), undefined);
    assert.equal(user_groups.get_user_group_from_name(admins.name).id, 1);
    assert.equal(user_groups.get_active_user_group_from_id(admins.id), admins);

    user_groups.add_in_realm(all);
    active_user_groups_array = user_groups.get_realm_user_groups();
    assert.equal(active_user_groups_array.length, 2);
    assert.equal(active_user_groups_array[1].name, 'Everyone');
    assert.equal(active_user_groups_array[0].name, 'new admins');

    assert(!user_groups.is_member_of(admins.id, 4));
    assert(user_groups.is_member_of(admins.id, 3));

    user_groups.add_members(all.id, [5, 4]);
    assert.deepEqual(user_groups.get_user_group_from_id(all.id).members,
                     Dict.from_array([1, 2, 3, 5, 4]));

    user_groups.remove_members(all.id, [1, 4]);
    assert.deepEqual(user_groups.get_user_group_from_id(all.id).members,
                     Dict.from_array([2, 3, 5]));

    assert(user_groups.is_user_group(admins));
    const object = {
        name: 'core',
        id: 3,
    };
    assert(!user_groups.is_user_group(object));

    user_groups.init();
    assert.equal(user_groups.get_realm_user_groups().length, 0);

    blueslip.set_test_data('error', 'Could not find user group with ID -1');
    assert.equal(user_groups.is_member_of(-1, 15), false);
    assert.equal(blueslip.get_test_logs('error').length, 1);
    blueslip.clear_test_data();
});
