function getHello() {
    const url = 'http://localhost:5000/hello'
    fetch(url)
    .then(response => response.json())  
    .then(json => {
        console.log(json);
        if (json == true){ 
            
            location.reload();}
    })
}

setInterval(function() {getHello()}, 1000); 