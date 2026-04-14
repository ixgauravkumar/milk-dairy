function addToCart(product) {
    fetch('/add-to-cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product: product })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        loadCart();
    });
}

function loadCart() {
    fetch('/get-cart')
    .then(res => res.json())
    .then(data => {
        let cartList = document.getElementById("cart-list");
        cartList.innerHTML = "";

        data.forEach(item => {
            let li = document.createElement("li");
            li.innerText = item;
            cartList.appendChild(li);
        });
    });
}

window.onload = loadCart;
