function doRefresh() {
    const url = 'http://localhost:5000/refresh_page'
    fetch(url)
    .then(response => response.json())  
    .then(json => {
        console.log(json);
        if (json == true){ 
            
            location.reload();}
    })
}
// Every 1 second do refresh check
setInterval(function() {doRefresh()}, 1000); 