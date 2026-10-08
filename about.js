// ===== About section =====
const facts = document.querySelectorAll('.fact');

// 1. Fade in each note when it scrolls into view
const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.3 });

facts.forEach((fact, i) => {
    fact.style.transitionDelay = (i * 0.2) + 's';
    observer.observe(fact);
});

// 2. Click a note to flip to its bonus fact
facts.forEach(fact => {
    const text = fact.querySelector('p');
    const original = text.innerHTML;

    fact.addEventListener('click', () => {
        fact.classList.toggle('flipped');
        if (fact.classList.contains('flipped')) {
            text.innerHTML = fact.dataset.more;
        } else {
            text.innerHTML = original;
        }
    });
});
