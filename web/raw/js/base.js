"use strict"

// credits http://www.hagenburger.net/BLOG/HTML5-Input-Placeholder-Fix-With-jQuery.html
jQuery.prototype.placeholder = function(cls){
    $(this).on('focus', function(){
        var self = $(this);
        if (self.val() == self.attr('placeholder')){
            self.val('');
            self.removeClass(cls);
        }
    });
    $(this).on('blur', function(){
        var self = $(this);
        if (self.val() == '' || self.val() == self.attr('placeholder')){
            self.val(self.attr('placeholder'));
            self.addClass(cls);
        }
    });
    $(this).blur();
}

jQuery.prototype.popup = function(selector, callback){
    var self = this;
    // hide and align the element
    self.hide(0, function(){
        self.css({
            'position': 'fixed',
            'top': '50%',
            'left': '50%',
            'margin-left': -self.width()/2,
            'margin-top': -self.height()/2,
        });
    });
    $(document).on('click', selector, function(){
        self.toggle(0, function(){
            if (callback){
                callback.call(self);
            }
        });
    });
}

jQuery.prototype.htmlScroll = function(data){
    var keepElements = {}
    $('.keep-scroll-position').each(function(i, e){
        keepElements[i] = e.scrollTop;
    });
    this.html(data);
    $('.keep-scroll-position').each(function(i, e){
        e.scrollTop = keepElements[i];
    });
}

document.scale = function(){
    var cls;
    var dimension = window.innerWidth > window.innerHeight ? window.innerWidth : window.innerHeight;
    var factor = Math.floor(dimension/350);

    switch (factor){
        case 0:
        case 1:
            cls = 'x-narrow';
            break;
        case 2:
            cls = 'narrow';
            break;
        case 3:
            break;
        case 4:
            cls = 'wide';
            break;
        default:
            cls = 'x-wide';
            break;
    }
    console.log('current factor is ' + factor);
    $('body').removeClass('x-narrow narrow wide x-wide').addClass(cls);
}
