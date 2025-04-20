document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('.star-score').forEach(ratingEl => {
        const score = parseFloat(ratingEl.dataset.score);  // get rating number

        // Clear if needed
        ratingEl.innerHTML = '';

        for (let i = 1; i <= 5; i++) {
            const star = document.createElement("span");
            star.innerHTML = '&#9733;'; // ★ Unicode star
            if(i <= Math.floor(score)){
                star.classList.add('filled');
            }
            else if((i - score) <= 0.5 && (i - score) > 0){
                star.classList.add('half-filled');
            }
            else if(i > score){
                star.classList.add('star');
            }
            star.style.fontSize = '20px';
            ratingEl.appendChild(star);
        }
    });
});