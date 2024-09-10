checkRouterStatus(IP)
{
    const url="http://${" + IP + "}/";
    // endpoint del router
    try {   
        const response = await fetch(url, { 
                                            method: 'GET',
                                            mode: 'no-cors'
                                            //ipotesi richieste: cors
        });
        if(response.ok) {
            console.log("Router funzionante");
            return true;
        }
        else {
            console.log("Nessuna risposta");
            return false;
        }
    } catch(error) {
        console.log("Errore");
        return false;
    }

}