document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('.star-score').forEach(ratingEl => {
        const score = parseFloat(ratingEl.dataset.score);  // get rating number

        // Clear if needed
        ratingEl.innerHTML = '';

        for (let i = 1; i <= 5; i++) {
            const star = document.createElement("span");
            star.innerHTML = '&#9733;'; // ★ Unicode star
            if(i <= score){
                star.style.color = 'gold';
            }
            else if(i > score){
                star.style.color = 'lightgray';
            }
            star.style.fontSize = '20px';
            ratingEl.appendChild(star);
        }
    });
});