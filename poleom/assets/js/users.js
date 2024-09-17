Users = function() {
    $('a[member]').on('click', {role: "member"}, this.set_role.bind(this));
    $('a[moderator]').on('click', {role: "moderator"}, this.set_role.bind(this));
    $('a[admin]').on('click', {role: "admin"}, this.set_role.bind(this));
    $('a[ban]').on('click', {state: "ban"}, this.ban.bind(this));
    $('a[unban]').on('click',{state: "unban"},  this.ban.bind(this));
    $('a[delete]').on('click', this.delete.bind(this));
}

Users.prototype.set_role = function(ev) {
    let $target = $(ev.target);
    let $name = $('[data=name]', $target.parent().parent());
    let question = "Do you want to make "+$name.text()+" as "+ev.data.role+"?";
    if (confirm(question)){
        $.ajax({url: "/users/"+$target.attr(ev.data.role),
                type: "put",
                accepts : {json: 'application/json'},
                    contentType: 'application/json',
                    data: JSON.stringify({
                        role: ev.data.role
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

Users.prototype.ban = function(ev) {
    let $target = $(ev.target);
    let $name = $('[data=name]', $target.parent().parent());
    let state = ev.data.state;
    let question = "Do you want to "+state+" "+$name.text()+"?";
    if (confirm(question)){
        $.ajax({url: "/users/"+$target.attr(state)+"/ban",
                type: state == "ban" ? "post" : "delete",
                success: function() {
                    location.reload();
                },
                error: function(xhr, status, http_status) {
                    alert("Server error "+http_status);
                }
        });
    }
}
Users.prototype.delete = function(ev) {
    let $target = $(ev.target);
    let $name = $('[data=name]', $target.parent().parent());
    let question = "Do you want to delete user "+$name.text()+"?";
    if (confirm(question)){
        $.ajax({url: "/users/"+$target.attr("delete"),
                type: "delete",
                success: function() {
                    location.reload();
                },
                error: function(xhr, status, http_status) {
                    alert("Server error "+http_status);
                }
        });
    }
}
