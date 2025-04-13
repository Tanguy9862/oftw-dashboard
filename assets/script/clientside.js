// Ensure the dash_clientside namespace exists
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {

    toggle_modal_data_source: function(n_clicks, opened) {
            if(n_clicks === undefined) {
                return window.dash_clientside.no_update;
            }
            return !opened;
    }
};