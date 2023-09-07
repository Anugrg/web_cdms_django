

function buildMap(mapContainer, L, conf){
    console.log(conf);
    let map = L.map(mapContainer);
    let center_lat = 25.0376
    let center_lon = 76.4563
    let width = 200;
    let height= 300;

    let areaSelect = L.areaSelect({
        width:width, height:height,
        minWidth:40, minHeight:40,
        minHorizontalSpacing:40, minVerticalSpacing:100
    });
    map.on('layeradd', function(){
        let bounds = areaSelect.getBounds();
        $("#inp_lat").val(bounds._northEast.lat.toPrecision(4))
        $('#inp_lat2').val(bounds._southWest.lat.toPrecision(4))
        $('#inp_lon').val(bounds._northEast.lng.toPrecision(4))
        $('#inp_lon2').val(bounds._southWest.lng.toPrecision(4))
    })
    map.setView([center_lat, center_lon], 4 );
    areaSelect.addTo(map);
    L.tileLayer(conf.URL, {
        attribution: '',
        maxZoom: 10,
        id: 'mapbox/outdoors-v11',
        tileSize: 512,
        zoomOffset: -1,
        accessToken: conf.accessToken,
    }).addTo(map);

    let bboxCoordinates = areaSelect.getBBoxCoordinates();
    areaSelect.on("change", function(){
        console.log("Bounds:", this.getBounds() );
        let bounds = this.getBounds();

        $("#inp_lat").val(bounds._northEast.lat.toPrecision(4))
        $('#inp_lat2').val(bounds._southWest.lat.toPrecision(4))
        $('#inp_lon').val(bounds._northEast.lng.toPrecision(4))
        $('#inp_lon2').val(bounds._southWest.lng.toPrecision(4))

    });

}

 function in_browser_download(filename) {

        const a = document.createElement("a");
        //const file = new Blob([content], { type: contentType });
        let img = document.querySelector('#graph')
        let imgPath = img.getAttribute('src')
        a.href = imgPath //URL.createObjectURL(file);
        a.download = filename;
        a.click();
    }

    function in_browser_preview(content, filename, contentType) {

        const file = new Blob([content], { type: contentType });
        document.querySelector('#graph').src = URL.createObjectURL(file);

    }

    function video_download(filename){

        const a = document.createElement("a")
        let vid = document.querySelector('source')
        let vidPath = vid.getAttribute('src')
        a.href = vidPath
        a.download = filename
        a.click();
        a.remove();

    }

function get_usr_assets(url){

    fetch(url)
    .then(r=>r.json())
    .then(resp => {
        var options = '<option >None</option>';

        resp['user_assets'].forEach((item)=>{

            let name = item['file'].split('/')[1];

            options += `<option value="${item['identifier']}">${name}</option>`;

        })
        $("#asset").html(options);
    })
}
