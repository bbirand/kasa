// leave at least 2 line with only a star on it below, or doc generation fails
/**
 *
 *
 * Placeholder for custom user javascript
 * mainly to be overridden in profile/static/custom/custom.js
 * This will always be an empty file in IPython
 *
 * User could add any javascript in the `profile/static/custom/custom.js` file
 * (and should create it if it does not exist).
 * It will be executed by the ipython notebook at load time.
 *
 * Same thing with `profile/static/custom/custom.css` to inject custom css into the notebook.
 *
 * Example :
 *
 * Create a custom button in toolbar that execute `%qtconsole` in kernel
 * and hence open a qtconsole attached to the same kernel as the current notebook
 *
 *    $([IPython.events]).on('app_initialized.NotebookApp', function(){
 *        IPython.toolbar.add_buttons_group([
 *            {
 *                 'label'   : 'run qtconsole',
 *                 'icon'    : 'icon-terminal', // select your icon from http://fortawesome.github.io/Font-Awesome/icons
 *                 'callback': function () {
 *                     IPython.notebook.kernel.execute('%qtconsole')
 *                 }
 *            }
 *            // add more button here if needed.
 *            ]);
 *    });
 *
 * Example :
 *
 *  Use `jQuery.getScript(url [, success(script, textStatus, jqXHR)] );`
 *  to load custom script into the notebook.
 *
 *    // to load the metadata ui extension example.
 *    $.getScript('/static/notebook/js/celltoolbarpresets/example.js');
 *    // or
 *    // to load the metadata ui extension to control slideshow mode / reveal js for nbconvert
 *    $.getScript('/static/notebook/js/celltoolbarpresets/slideshow.js');
 *
 *
 * @module IPython
 * @namespace IPython
 * @class customjs
 * @static
 */

// Hide toolbar by default
$([IPython.events]).on("app_initialized.NotebookApp", function () {
    $('div#maintoolbar').hide();
});


//$([IPython.events]).on('notebook_loaded.Notebook', function(){
//    console.log("Hellow from ipython");
//});

function simplify_design(){

    // Remove all stylesheets except 'custom.css'
    $('head link, head style').each(function(){ 
        if (this.href && this.href.indexOf('custom.css') < 0) { 
            this.remove();
        }
    });

    // Remove some of the unnecessary elements
    $('div#maintoolbar').css('display','none');
    $('button.close').css('display','none');
    //$('div.input').css('display','none');
    $('div.input').hide();
    $('div#menubar-container').css('display','none');
    $('div#header').hide();
    $('div.prompt').hide();
    $('div#pager_splitter').hide();

    // Also remove border from selected cell
    $('div.cell.selected').css('border','none');
}

function style_home() {
    $('div#notebook_list div.list_item').each(function() {
        this.find('span.item_name').html("yo");
    });

}

//$([IPython.events]).on('notebook_loaded.Notebook', function(){
//$([IPython.events]).on('app_initialized.NotebookApp', function(){
//    console.log("app intialized");
//   //console.log(document.location.search);
//});


// Remove the unnecessary stuff as early as possible
$(document).ready(function(){
    if (document.location.pathname == "/tree" && document.location.search == "?hide") {
      simplify_design();
    }
});

$([IPython.events]).on('status_started.Kernel', function() {
   // When the kernel has started, run all the cells
   //console.log('Started kernel');
   IPython.notebook.execute_all_cells();

   // Simplify as necessary
   if (document.location.search == "?hide") {
      //console.log("simplifying design");
      simplify_design();
   }
});

// Custom widget code for SensorWidget
require(["widgets/js/widget"], function(WidgetManager){

    function display_content(w) {
        str = '<div class="values">';
        tuple = w.model.get('value');
        var i = 1
        for (x in tuple) {
            str += '<span class="value">' + tuple[x].toFixed(2) + '</span>';
            //str += '<span class="unit">' + w.model.get('sensor_unit') + '</span>';
            if (i < tuple.length) {
                str += ', ';
            }
            i++;
        }
        str += '<span class="unit">' + w.model.get('sensor_unit') + '</span>';
        str += '</div>';

        str += '<span class="type">' + w.model.get('sensor_type') + '</span>';

        return str;
    }
    
    // Define the DatePickerView
    var SensorView = IPython.DOMWidgetView.extend({
        render: function(){
            // this.$el is an empty div in which we will style the controle
            this.$sensor_div = $('<div class="sensor">' + display_content(this) 
                                + '</div>')
                                 .appendTo(this.$el);
        },

        update: function() {
            this.$sensor_div.html(display_content(this));
            return SensorView.__super__.update.apply(this);
        },
        
        /**        
        // Tell Backbone to listen to the change event of input controls (which the HTML date picker is)
        events: {"change": "handle_date_change"},
        
        // Callback for when the date is changed.
        handle_date_change: function(event) {
            this.model.set('value', this.$date.val());
            this.touch();
        },
        */
    });
    // Register the SensorView with the widget manager.
    WidgetManager.register_widget_view('TupleSensorView', SensorView);
});


// Custom widget code for SensorWidget
require(["widgets/js/widget"], function(WidgetManager){

    function display_content(w) {
       return '<span class="value">'+ w.model.get('value').toFixed(2) + '</span><span class="unit">' +
              w.model.get('sensor_unit') + '</span><br/><span class="type">' + 
              w.model.get('sensor_type') + '</span>'
    }
    
    // Define the DatePickerView
    var SensorView = IPython.DOMWidgetView.extend({
        render: function(){
            // this.$el is an empty div in which we will style the controle
            this.$sensor_div = $('<div class="sensor">' + display_content(this) 
                                + '</div>')
                                 .appendTo(this.$el);
        },

        update: function() {
            this.$sensor_div.html(display_content(this));
            return SensorView.__super__.update.apply(this);
        },
        
        /**        
        // Tell Backbone to listen to the change event of input controls (which the HTML date picker is)
        events: {"change": "handle_date_change"},
        
        // Callback for when the date is changed.
        handle_date_change: function(event) {
            this.model.set('value', this.$date.val());
            this.touch();
        },
        */
    });
    // Register the SensorView with the widget manager.
    WidgetManager.register_widget_view('ScalarSensorView', SensorView);
});



/*
 * WeMo Switch Widget
 */
require(["widgets/js/widget"], function(WidgetManager) {

    function display_content(w) {
        astr = "<span class='status'>";
        if (w.model.get('value')) {
            astr += 'On';  
        }
        else {
            astr += 'Off';
        }
        astr += "</span>";
        astr += "<br/><span class='description'>" + w.model.get('description') + "</span>";

        return astr
    }
    
    var WeMoSwitchView = IPython.DOMWidgetView.extend({
        render: function() {
            console.log('render');
            console.log(display_content(this));
            // this.$el is an empty div in which we will style the control
            this.$wemo_div = $('<div class="wemo">' + display_content(this) + '</div>')
                              .appendTo(this.$el);
        },

        update: function() {
            console.log('update');
            this.$wemo_div.html(display_content(this));
            return WeMoSwitchView.__super__.update.apply(this);
        },
        
        // Tell Backbone to listen to the change event of input controls (which the HTML date picker is)
        events: {"click": "handle_click"},
        
        // Callback for when the date is changed.
        handle_click: function(event) {
            this.model.set('value', !this.model.get('value'));
            this.touch();
        },
    });
    
    // Register the WeMoSwitchView with the widget manager.
    WidgetManager.register_widget_view('WeMoSwitchView', WeMoSwitchView);
});
 
// Custom widget code for Foscam
require(["widgets/js/widget"], function(WidgetManager){

    function display_content(w) {
       return '<iframe width="640" height="480" frameborder="0" src="http://'+ w.model.get('ip_address') + '/live.htm" name="main" scrolling="auto" marginwidth="0" marginheight="0"></iframe>'
    }
    
    var FoscamView = IPython.DOMWidgetView.extend({
        render: function(){
            // this.$el is an empty div in which we will style the controle
            this.$foscam_div = $('<div class="foscam">' + display_content(this) 
                                + '</div>')
                                 .appendTo(this.$el);
        },

        update: function() {
            this.$foscam_div.html(display_content(this));
            return FoscamView.__super__.update.apply(this);
        },
    });
    
    WidgetManager.register_widget_view('FoscamView', FoscamView);
});

