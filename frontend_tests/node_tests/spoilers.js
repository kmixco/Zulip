set_global('$', global.make_zjquery());
zrequire('spoilers');

// This function is taken from rendered_markdown.js and slightly modified.
const $array = (array) => {
    const each = (func) => {
        array.forEach((elem, index) => {
            func.call(this, index, elem);
        });
    };
    return {each};
};

const get_spoiler_elem = (title) => {
    const block = $.create(`block-${title}`);
    const header = $.create(`header-${title}`);
    const content = $.create(`content-${title}`);
    header.text(title);
    block.set_find_results('.spoiler-header', header);
    block.set_find_results('.spoiler-content', content);
    return block;
};

run_test('hide spoilers in notifications', () => {
    const root = $.create('root element');
    const spoiler_1 = get_spoiler_elem('this is the title');
    const spoiler_2 = get_spoiler_elem('');
    root.set_find_results('.spoiler-block', $array([spoiler_1, spoiler_2]));
    spoilers.hide_spoilers_in_notification(root);
    assert.equal(spoiler_1.find('.spoiler-header').text(), 'this is the title (…)');
    assert.equal(spoiler_2.find('.spoiler-header').text(), '(…)');
});
