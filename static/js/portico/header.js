$(() => {
    $('.portico-header li.logout').on('click', () => {
        $('#logout_form').submit();
        return false;
    });

    $("body").click((e) => {
        const $this = $(e.target);

        if ($this.closest(".dropdown .dropdown-pill").length > 0 && !$(".dropdown").hasClass("show")) {
            $(".dropdown").addClass("show");
        } else if (!$this.is(".dropdown ul") && $this.closest(".dropdown ul").length === 0) {
            $(".dropdown").removeClass("show");
        }
    });
});
