"use strict"

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
        callback(false);
        return;
    }
    options = options || {};
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
        audio.play();
        return;
    }
    // create a new element...
    ($('<audio>')
        .css({display: 'none'})
        .attr($.extend(options, {preload:'preload', src: src}))
        .bind('loadeddata', function(){
            if (typeof options.volume != 'undefined'){
                this.volume = options.volume;
            }
            this.callback = callback;
            var self = this;
            $(this).bind('ended', function(){
                if (self.callback){
                    self.callback(true);
                }
            });
            // ...and playback it right away
            this.play();
        })
        .appendTo('body')
    );
}