Message = function (message, type = 'info'){
    let symbol = '';
    if (type == 'info') symbol = '&#x2713;';
    if (type == 'error') symbol = '!';

    let $btn = $('<button>')
        .text('Close')
        .on('click', this.close.bind(this));
    this.$dom = $('<div>',  {'class': 'message '+type})
                    .append($('<div>', {'class': 'content'})
                        .append($('<div>', {'class': 'symbol'})
                            .append(symbol))
                        .append($('<div>', {'class': 'text'})
                            .text(message))
                        .append($btn));
}

Message.prototype.appendTo = function(target){
    this.$dom.appendTo(target);
}

Message.prototype.insertBefore = function(target){
    this.$dom.insertBefore(target);
}

Message.prototype.insertAfter = function(target){
    this.$dom.insertAfter(target);
}

Message.prototype.close = function(){
    this.$dom.detach();
    delete(this);
}
