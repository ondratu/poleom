SectionUsers = function(dom, section_id) {
    this.$dom = $(dom);
    this.$list_box = $('.list-box', this.$dom);
    this.$search = $('input[name=search]', this.$dom);
    this.$search_box = $('.search-box', this.$dom);
    this.section_id = section_id;

    this.$search.on("input", this.search.bind(this));
    this.reload();
}

SectionUsers.prototype.search = function() {
    $.ajax({url: "/users/search?q="+this.$search.val(),
            type: "get",
            context: this,
            success: function(data) {
                this.refresh_search(data);
            },
            error: function(xhr, status, http_status) {
                alert("Server error "+http_status);
            }
    });
}

SectionUsers.prototype.add_user = function(ev) {
    let user_id = $(ev.target).attr('user_id');

    $.ajax({url: "/sections/"+this.section_id+"/users/"+user_id,
            type: "post",
            context: this,
            success: function() {
                this.reload();
            },
            error: function(xhr, status, http_status) {
                if (xhr.status == 409) {
                    console.log("User "+user_id+" is exist on list yet");
                    // TODO: probliknout uživatele v druhém panelu
                    return;
                }
                alert("Server error "+http_status);
            }
    });
}

SectionUsers.prototype.remove_user = function(ev) {
    let user_id = $(ev.target).attr('user_id');

    $.ajax({url: "/sections/"+this.section_id+"/users/"+user_id,
            type: "delete",
            context: this,
            success: function() {
                this.reload();
            },
            error: function(xhr, status, http_status) {
                   alert("Server error "+http_status);
            }
    });

}

SectionUsers.prototype.reload = function() {
    $.ajax({url: "/sections/"+this.section_id+"/users",
            type: "get",
            context: this,
            success: function(data) {
                this.refresh(data);
            },
            error: function(xhr, status, http_status) {
                alert("Server error "+http_status);
            }
    });
}

SectionUsers.prototype.refresh_search = function(data) {
    this.$search_box.empty();
    for (let user of data.users) {
        $('<div>', {user_id: user.user_id})
            .text(user.name)
            .attr("title", "Add user to list")
            .appendTo(this.$search_box)
            .on('click', this.add_user.bind(this));
    }
}

SectionUsers.prototype.refresh = function(data) {
    this.$list_box.empty();
    for (let user of data.users) {
        $('<div>', {user_id: user.user_id})
            .text(user.name)
            .attr("title", "Remove user from list")
            .appendTo(this.$list_box)
            .on('click', this.remove_user.bind(this));
    }
}
