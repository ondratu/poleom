Toggle = function(button){
    this.$button = $(button);

    this.init();
}

Toggle.prototype.init = function(){
    this.$button.on('click', function() {
        this.$button.next().slideToggle;
    });
}
