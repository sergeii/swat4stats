"use strict"

if (Storage){
    // http://stackoverflow.com/questions/2010892/storing-objects-in-html5-localstorage
    Storage.prototype.setObject = function(key, value) {
        this.setItem(key, JSON.stringify(value));
    }

    Storage.prototype.getObject = function(key) {
        var value = this.getItem(key);
        return value && JSON.parse(value);
    }
}

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
    var obj = this;
    var self = $(obj);
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
                callback.call(obj);
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

document.playback = function(src, options, callback){
    var audio;

    if (!document.playback.enabled){
        if (callback){
            callback(false);
        }
        return;
    }
    options = options || {};
    /*

    // loop through the existing audio tags 
    // and attempt to find the one with provided src
    $('audio').each(function(){
        // this.src is an absolute path
        if ($(this).attr('src') == src){
            console.log(src + ' is cached');
            audio = this;
        }
    });
    if (audio){
        audio.callback = callback;
        audio.load();
        return;
    }
    // create a new element...
    */
    ($('<audio>')
        .css({display: 'none'})
        .attr($.extend(options, {preload: 'preload', src: src}))
        .bind('loadeddata', function(){
            var self = this;
            self.callback = callback;
            if (typeof options.volume != 'undefined'){
                this.volume = options.volume;
            }
            $(self).bind('ended', function(){
                if (self.callback){
                    self.callback(true);
                    $(self).remove();
                }
            });
            // ...and playback it right away
            this.play();
        })
        .appendTo('html')
    );
}