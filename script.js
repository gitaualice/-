// ===== Gallery filters =====
const filterButtons = document.querySelectorAll('.filter-btn');
const photos = Array.from(document.querySelectorAll('.photo-grid img'));

filterButtons.forEach(button => {
    button.addEventListener('click', () => {
        // highlight the clicked button
        filterButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // show photos that match the filter, hide the rest
        const filter = button.dataset.filter;
        photos.forEach(photo => {
            if (filter === 'all' || photo.dataset.category === filter) {
               photo.style.display = '';
            } else {
                photo.style.display = 'none';
            }
        });
    });
});


// ===== Lightbox (full-screen viewer with arrows) =====
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const caption = document.getElementById('lightbox-caption');
const counter = document.getElementById('lightbox-counter');
const closeBtn = lightbox.querySelector('.close');
const prevBtn = lightbox.querySelector('.lb-prev');
const nextBtn = lightbox.querySelector('.lb-next');

let currentList = [];   // the photos you can scroll through (only the ones the filter shows)
let currentIndex = 0;

function visiblePhotos() {
    return photos.filter(photo => photo.style.display !== 'none');
}

function showPhoto(index) {
    // wrap around: after the last photo comes the first, and before the first comes the last
    currentIndex = (index + currentList.length) % currentList.length;
    const photo = currentList[currentIndex];

    lightboxImg.classList.remove('fade-in');
    void lightboxImg.offsetWidth;            // restart the fade animation
    lightboxImg.src = photo.src;
    lightboxImg.alt = photo.alt;
    lightboxImg.classList.add('fade-in');

    caption.textContent = photo.alt;
    counter.textContent = (currentIndex + 1) + ' / ' + currentList.length;

    // load the next and previous photos in the background so arrows feel instant
    [currentIndex + 1, currentIndex - 1].forEach(i => {
        const neighbor = currentList[(i + currentList.length) % currentList.length];
        new Image().src = neighbor.src;
    });
}

function openLightbox(photo) {
    currentList = visiblePhotos();
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';  // stop the page scrolling behind the viewer
    showPhoto(currentList.indexOf(photo));
}

function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
}

function nextPhoto() { showPhoto(currentIndex + 1); }
function prevPhoto() { showPhoto(currentIndex - 1); }

photos.forEach(photo => {
    photo.addEventListener('click', () => openLightbox(photo));
});

nextBtn.addEventListener('click', nextPhoto);
prevBtn.addEventListener('click', prevPhoto);
closeBtn.addEventListener('click', closeLightbox);

// click the dark background to close
lightbox.addEventListener('click', e => {
    if (e.target === lightbox) {
        closeLightbox();
    }
});

// keyboard: left/right arrows to move, Escape to close
document.addEventListener('keydown', e => {
    if (!lightbox.classList.contains('open')) return;
    if (e.key === 'ArrowRight') nextPhoto();
    if (e.key === 'ArrowLeft') prevPhoto();
    if (e.key === 'Escape') closeLightbox();
});

// phones: swipe left or right
let touchStartX = 0;
lightbox.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].clientX;
}, { passive: true });

lightbox.addEventListener('touchend', e => {
    const distance = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(distance) > 50) {
        distance < 0 ? nextPhoto() : prevPhoto();
    }
});