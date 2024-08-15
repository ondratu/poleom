DocutilsEditor = function(source){
    this.$source = $(source);

    this.init();
}

DocutilsEditor.prototype.init = function(){
    this.$container = $('<div>')
            .addClass('editor')
            .insertBefore(this.$source);
    this.$source.detach();
    this.$container.append(this.$source);

    this.$source.addClass('source');

    this.$btn_edit = $('<button>', {type: 'button'})
            .addClass('btn active')
            .text("Write")
            .on('click', this.edit.bind(this));
    this.btn_edit_color = this.$btn_edit.css('color');
    this.$btn_preview = $('<button>', {type: 'button'})
            .addClass('btn')
            .text("Preview")
            .on('click', this.preview.bind(this));

    this.$toolbar = $('<div>')
        .addClass('btn-group')
        .append(this.$btn_edit)
        .append(this.$btn_preview)
        .insertBefore(this.$container);

    this.$preview = $('<div>')
        .addClass('preview')
        .css('display', 'none')
        .css('height', this.$source.css('height'))
        .css('overflow', 'auto')
        .insertAfter(this.$source);

    this.$syntax_lines = $('<div>').addClass('lines');
    this.$syntax = $('<div>')
        .addClass('syntax')
        .css('border', '0')
        .css('overflow', 'hidden')
        .append(this.$syntax_lines)
        .insertBefore(this.$source);


    this.syntax_lines();
    this.$source.on('input', this.input.bind(this));
}


DocutilsEditor.prototype.syntax_lines = function(ev){
    let count = this.$source.val().split('\n').length;
    let lines = this.$syntax_lines.children();
    if (lines.length < count){ // append lines
        let to_add = count - lines.length;
        for (let i = 0; i < to_add; i++){
            //this.$syntax_lines.append($('<div>').html(lines.length + i + 1 +':'));
            this.$syntax_lines.append($('<div>').html('&nbsp;'));
        }
    } else if (lines.length > count) {
        let to_remove = lines.length - count;
        for (let i = 0; i < to_remove; i++){
            this.$syntax_lines.children().last().remove();
        }
    }
}

DocutilsEditor.prototype.preview = function(ev){
    if (this.$syntax.css('display') == 'none'){
        return;
    }

    this.$preview.css('height', this.$source.css('height'));
    this.$syntax.css('display', 'none');
    this.$source.css('display', 'none');
    this.$preview.css('display', 'block');

    this.$btn_preview.addClass('active');
    this.$btn_edit.removeClass('active');
    this.preview_call(ev);
}

DocutilsEditor.prototype.edit = function(ev){
    this.$preview.css('display', 'none');
    this.$source.css('display', 'block');
    this.$syntax.css('display', 'block');

    this.$btn_edit.addClass('active');
    this.$btn_preview.removeClass('active');
}

DocutilsEditor.prototype.input = function(ev){
    if (this.$btn_edit.css('color') == this.btn_edit_color){
        this.$btn_edit.css('color', 'red');
        this.$btn_edit.css('color', this.btn_edit_color);
        $('div', this.$syntax_lines)
            .removeClass('error-line')
            .tooltip('destroy');
    }
    this.syntax_lines();
}

DocutilsEditor.prototype.preview_call = function(ev){
    $.ajax({url: '/preview',
            type: 'post',
            data: {'source': this.$source.val()},
            context: this,
            success: function (data) {
                this.$preview.html(data.html);
                //this.$btn_preview.attr("disabled", "disabled");

                if (data.errors.length){
                    this.$btn_edit.css('color', 'red');
                    for (var i = 0; i < data.errors.length; i++){
                        error = data.errors[i];
                        line = error[0];
                        type = error[1];
                        level = error[2];
                        text = error[3];

                        var xline = $('div:nth-child('+line+')', this.$syntax_lines);
                        xline.addClass('error-line');
                        xline.html(text);
                    }
                } else {
                    this.$btn_edit.css('color', this.btn_edit_color);
                }
            },
            error: function(xhr, status, http_status) {
                console.error(http_status);
                this.$preview.html('<h3>Preview Request Error</h3>');
            }
        });
}
