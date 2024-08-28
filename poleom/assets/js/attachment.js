Attachment = function(input, editor){
    this.$input = $(input);
    this.$editor = $(editor);
    this.$input.on("change", this.add_file_input.bind(this));

    $('a[paste]').on('click', this.paste_url.bind(this));
    $('a[remove]').on('click', this.remove_attachment.bind(this));
}

Attachment.prototype.add_file_input = function(ev){
    let $input = $('<input>', {type: "file", name: "attachments"})
        .on("change", this.add_file_input.bind(this));

    this.$input
        .off("change")
        .after($input)
        .after($('<a>', {title: "remove"})
          .addClass('button')
          .html('&#10799;')
          .on("click", this.remove_file_input.bind()));

    this.$input = $input;
}

Attachment.prototype.remove_file_input = function(ev){
    let $target = $(ev.target);
    $target.off("click");
    $target.prev().detach();
    $target.detach();
}

Attachment.prototype.insert_text = function(text) {
    let pos = this.$editor[0].selectionStart;
    console.log(pos);

    let dst = this.$editor.val();
    this.$editor.val(dst.slice(0, pos) + text + dst.slice(pos));
}

Attachment.prototype.paste_url = function(ev) {
    let $target = $(ev.target);
    let url = "["+$target.attr("file_name")
                  +"](/a/"+$target.attr("paste")
                  +"/"+$target.attr("file_name")
                  +")";
    // navigator.clipboard.writeText(url);
    if (this.$editor.css("display") != "none"){
        this.insert_text(url);
    }
}

Attachment.prototype.remove_attachment = function(ev) {
    let $target = $(ev.target);
    let ok = confirm("Do you want to delete `"+$target.attr("file_name")+"`?");
    if (ok == true) {
        let url = "/a/"+$target.attr("remove");
        $.ajax({url: url,
                type: 'delete',
                success: function() {
                    $target.parent().parent().detach();
                },
                error: function(xhr, status, http_status) {
                    alert("Server error "+http_status);
                }
        });
    }
}
