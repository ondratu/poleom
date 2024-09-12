Sections = function() {
    $('a[up]').on('click', {attr: "up", weight: -1}, this.set_weight.bind(this));
    $('a[down]').on('click', {attr: "down", weight: 1}, this.set_weight.bind(this));
    $('a[cmd=archive]').on('click', {state: "archive"}, this.set_state.bind(this));
    $('a[cmd=lock]').on('click', {state: "lock"}, this.set_state.bind(this));
    $('a[cmd=open]').on('click', {state: "open"}, this.set_state.bind(this));
    $('a[public]').on('click', {attr: "public"}, this.set_private.bind(this));
    $('a[private]').on('click', {attr: "private"}, this.set_private.bind(this));
}

Sections.prototype.set_weight = function(ev) {
    let $target = $(ev.target);
    let direction = ev.data.attr;

    $.ajax({url: "/sections/"+$target.attr(direction),
            type: "patch",
            accepts : {json: 'application/json'},
            contentType: 'application/json',
            data: JSON.stringify({
                weight: ev.data.weight
            }),
            success: function() {
                location.reload();
            },
            error: function(xhr, status, http_status) {
                alert("Server error "+http_status);
            }
    });
}

Sections.prototype.set_state = function(ev) {
    let $target = $(ev.target);
    let $title = $('[data=title]', $target.parent().parent());
    let question = "Do you want to "+ev.data.state+" "+$title.text()+"?";

    // cause $(ev.target).attr("open") returns "open" :-/
    if (confirm(question)){
        state = ev.data.state;
        if (state == "lock"){ state = "locked"; }
        else if (state == "archive"){ state = "archived"; }

        $.ajax({url: "/sections/"+$target.attr("section-id"),
                type: "patch",
                accepts : {json: 'application/json'},
                contentType: 'application/json',
                data: JSON.stringify({
                    state: state
                }),

                success: function() {
                    location.reload();
                },
                error: function(xhr, status, http_status) {
                    alert("Server error "+http_status);
                }
        });
    }
}

Sections.prototype.set_private = function(ev) {
    let $target = $(ev.target);
    let $title = $('[data=title]', $target.parent().parent());
    let question = "Do you want set "+$title.text()+" as "+ ev.data.attr+"?";

    if (confirm(question)){
        $.ajax({url: "/sections/"+$target.attr(ev.data.attr),
                type: "patch",
                accepts : {json: 'application/json'},
                contentType: 'application/json',
                data: JSON.stringify({
                    "private": (ev.data.attr == "private")
                }),

                success: function() {
                    location.reload();
                },
                error: function(xhr, status, http_status) {
                    alert("Server error "+http_status);
                }
        });
    }
}
