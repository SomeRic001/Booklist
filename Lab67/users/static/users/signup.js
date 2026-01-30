document.addEventListener('DOMContentLoaded',()=>{
    const error = document.body.dataset.error;
    if (error){
        alert(error);
    }
})