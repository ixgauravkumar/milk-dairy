// ✅ ADD ITEM
function addToCart(product, price) {
    fetch('/add-to-cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product: product,
            price: price
        })
    })
    .then(res => res.json())
    .then(() => {
        loadCart();
    });
}

// ✅ REMOVE ITEM
function removeFromCart(index) {
    fetch('/remove-from-cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index })
    })
    .then(res => res.json())
    .then(() => {
        loadCart();
    });
}

// ✅ LOAD CART
function loadCart() {
    fetch('/get-cart')
    .then(res => res.json())
    .then(data => {

        let cartList = document.getElementById("cart-list");
        let totalBox = document.getElementById("total");
        let hiddenInput = document.getElementById("cart_data");

        cartList.innerHTML = "";

        let total = 0;

        data.forEach((item, index) => {
            total += item.price;

            let li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center";

            li.innerHTML = `
                <span>${item.product} - ₹${item.price}</span>
                <button onclick="removeFromCart(${index})"
                        style="color:red;border:none;background:none;font-size:18px;">
                    ❌
                </button>
            `;

            cartList.appendChild(li);
        });

        totalBox.innerText = total;

        // ✅ SEND CART TO BACKEND
        hiddenInput.value = JSON.stringify(data);
    });
}

// ✅ AUTO LOAD
window.onload = loadCart;
