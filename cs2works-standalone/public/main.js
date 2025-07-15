// Smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Pre-order button functionality
    const preOrderButtons = document.querySelectorAll('.btn-primary');
    preOrderButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Add loading state
            const originalText = this.textContent;
            this.textContent = 'Processing...';
            this.disabled = true;
            
            // Simulate processing
            setTimeout(() => {
                alert('Pre-order functionality will be implemented here. This would typically redirect to a payment page or cart.');
                this.textContent = originalText;
                this.disabled = false;
            }, 1000);
        });
    });

    // Learn More button functionality
    const learnMoreButtons = document.querySelectorAll('.btn-secondary');
    learnMoreButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productSection = document.querySelector('#product');
            if (productSection) {
                const offsetTop = productSection.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Navbar background on scroll
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.98)';
            navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
            navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = 'none';
        }
    });

    // Gallery thumbnail functionality (placeholder)
    const galleryThumbnails = document.querySelectorAll('.gallery-thumbnails .placeholder-image');
    const mainImage = document.querySelector('.gallery-main .placeholder-image');
    
    galleryThumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', function() {
            // Remove active class from all thumbnails
            galleryThumbnails.forEach(thumb => thumb.classList.remove('active'));
            
            // Add active class to clicked thumbnail
            this.classList.add('active');
            
            // Update main image (in a real implementation, this would change the image source)
            const mainContent = mainImage.querySelector('.placeholder-content');
            mainContent.innerHTML = `
                <span>Product Image ${index + 1}</span>
                <small>CS2 Figurine - View ${index + 1}</small>
            `;
        });
    });

    // Add hover effects to features
    const features = document.querySelectorAll('.feature');
    features.forEach(feature => {
        feature.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        feature.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Animate stats on scroll
    const stats = document.querySelectorAll('.stat h3');
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px 0px -50px 0px'
    };

    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const stat = entry.target;
                const finalValue = stat.textContent;
                
                // Animate the number
                let currentValue = 0;
                const increment = parseInt(finalValue) / 50;
                const timer = setInterval(() => {
                    currentValue += increment;
                    if (currentValue >= parseInt(finalValue)) {
                        stat.textContent = finalValue;
                        clearInterval(timer);
                    } else {
                        stat.textContent = Math.floor(currentValue);
                    }
                }, 30);
                
                statsObserver.unobserve(stat);
            }
        });
    }, observerOptions);

    stats.forEach(stat => {
        statsObserver.observe(stat);
    });

    // Add CSS for active thumbnail state
    const style = document.createElement('style');
    style.textContent = `
        .gallery-thumbnails .placeholder-image.active {
            border-color: #000;
            background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
        }
        
        .feature {
            transition: transform 0.3s ease;
        }
    `;
    document.head.appendChild(style);

    // Console welcome message
    console.log('🎮 CS2 Figurine Website Loaded Successfully!');
    console.log('Ready for premium gaming collectibles.');
});

// --- HERO VIDEO HEADER LOGIC ---
document.addEventListener('DOMContentLoaded', function() {
  var heroVideo = document.getElementById('heroVideo');
  var heroOverlay = document.getElementById('heroOverlay');
  if (heroVideo && heroOverlay) {
    function updateOverlay() {
      if (heroVideo.paused || heroVideo.ended) {
        heroOverlay.classList.remove('hidden');
      } else {
        heroOverlay.classList.add('hidden');
      }
    }
    heroVideo.addEventListener('play', updateOverlay);
    heroVideo.addEventListener('pause', updateOverlay);
    heroVideo.addEventListener('ended', updateOverlay);
    // Initial state
    updateOverlay();
  }
});

// --- PRODUCT SECTION INTERACTIVITY ---
document.addEventListener('DOMContentLoaded', function() {
  // Quantity buttons (1–5)
  const qtyControls = document.getElementById('qty-controls');
  if (qtyControls) {
    let selectedQty = 1;
    for (let i = 1; i <= 5; i++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'quantity-btn';
      btn.textContent = i;
      btn.dataset.value = i;
      if (i === selectedQty) btn.classList.add('active');
      btn.addEventListener('click', () => {
        qtyControls.querySelectorAll('.quantity-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedQty = i;
      });
      qtyControls.appendChild(btn);
    }
  }

  // Lightbox & zoom setup
  const accessoryImg = document.getElementById('accessory-img');
  const viewerImg     = document.getElementById('viewer-img');
  const lightbox      = document.getElementById('lightbox');
  const lightboxImg   = document.getElementById('lightbox-img');
  const closeBtn      = document.querySelector('.close-lightbox');
  let zoomed = false;
  const resetZoom = () => { lightboxImg.style.transform = 'scale(1)'; zoomed = false; };
  const openBox    = src => { lightboxImg.src = src; lightbox.classList.add('active'); resetZoom(); };
  const closeBox   = () => { lightbox.classList.remove('active'); resetZoom(); };
  viewerImg   && viewerImg.addEventListener('click', () => openBox(viewerImg.src));
  accessoryImg&& accessoryImg.addEventListener('click', e => openBox(e.target.src));
  closeBtn    && closeBtn.addEventListener('click', closeBox);
  lightbox    && lightbox.addEventListener('click', e => { if (e.target === lightbox) closeBox(); });
  lightboxImg && lightboxImg.addEventListener('click', e => {
    if (!zoomed) {
      const r = lightboxImg.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width) * 100;
      const y = ((e.clientY - r.top ) / r.height)* 100;
      lightboxImg.style.transformOrigin = `${x}% ${y}%`;
      lightboxImg.style.transform = 'scale(2)';
      zoomed = true;
    } else resetZoom();
  });

  // Carousel & gallery variables
  const prevBtn      = document.getElementById('prevBtn');
  const nextBtn      = document.getElementById('nextBtn');
  const dotContainer = document.getElementById('dotContainer');
  const currentCaption = document.getElementById('currentCaption');
  const imageCount     = document.getElementById('imageCount');
  const prevName     = document.getElementById('prevName');
  const currentName  = document.getElementById('currentName');
  const nextName     = document.getElementById('nextName');
  const angleLeftBtn = document.getElementById('myAngleLeft');
  const angleRightBtn= document.getElementById('myAngleRight');

  const urls = {
    vice: {
      angles: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_ViceGloves_1.jpg?v=1750332570",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_ViceGloves_2.jpg?v=1750332570",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_ViceGloves_3.jpg?v=1750332570",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_ViceGloves_4.jpg?v=1750332570"
      ],
      skins: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_ViceGloves_1.jpg?v=1750332554",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_fade.jpg?v=1749907969",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_arabesque.jpg?v=1749907724",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_hotrod.jpg?v=1749907940",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_bluephosphor.jpg?v=1749907774",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_ruby.jpg?v=1749907792",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_emerald.jpg?v=1749908821",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/vice_sapphire.jpg?v=1750008665"
      ]
    },
    pandora: {
      angles: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_PandorasBox_1.jpg?v=1750332630",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_PandorasBox_2.jpg?v=1750332630",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_PandorasBox_3.jpg?v=1750332630",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_PandorasBox_4.jpg?v=1750332630"
      ],
      skins: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_PandorasBox_1.jpg?v=1750332619",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_fade.jpg?v=1749907926",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_arabesque.jpg?v=1749918916",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_hotrod.jpg?v=1749907952",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_bluephosphor.jpg?v=1749907839",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_ruby.jpg?v=1749908644",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_emerald.jpg?v=1749907913",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/pandora_sapphire.jpg?v=1750008691"
      ]
    },
    hedge: {
      angles: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_HedgeMaze_1.jpg?v=1750332418",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_HedgeMaze_2.jpg?v=1750332418",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_HedgeMaze_3.jpg?v=1750332418",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_HedgeMaze_4.jpg?v=1750332418"
      ],
      skins: [
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/MiamiDarrylFigurine_HedgeMaze_1.jpg?v=1750332352",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_fade.jpg?v=1749907822",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_arabesque.jpg?v=1749907808",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_hotrod.jpg?v=1749908427",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_bluephosphor.jpg?v=1749907985",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_ruby.jpg?v=1749908002",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_emerald.jpg?v=1749908692",
        "https://cdn.shopify.com/s/files/1/0745/6482/9415/files/hedge_sapphire.jpg?v=1750008689"
      ]
    }
  };

  const gloves = {
    vice:    ["Vice Gloves","AWP | Fade","AK-47 | Gold Arabesque","M4A1-S | Hot Rod","M4A1-S | Blue Phosphor","★ Karambit | Ruby","★ Karambit | Emerald","★ M9 Bayonet | Sapphire"],
    pandora: ["Pandora's Box Gloves","AWP | Fade","AK-47 | Gold Arabesque","M4A1-S | Hot Rod","M4A1-S | Blue Phosphor","★ Karambit | Ruby","★ Karambit | Emerald","★ M9 Bayonet | Sapphire"],
    hedge:   ["Hedge Maze Gloves","AWP | Fade","AK-47 | Gold Arabesque","M4A1-S | Hot Rod","M4A1-S | Blue Phosphor","★ Karambit | Ruby","★ Karambit | Emerald","★ M9 Bayonet | Sapphire"]
  };

  let currentGlove   = 'pandora';
  let currentSet     = urls[currentGlove];
  let nameSet        = gloves[currentGlove];
  let index          = 0;
  let currentAngle   = 0;
  let showingAngles  = false;

  function buildDots() {
    if (!dotContainer) return;
    dotContainer.innerHTML = '';
    (showingAngles ? [0,1,2,3] : currentSet.skins)
      .forEach((_, i) => {
        const d = document.createElement('span');
        d.className = 'dot' + ((showingAngles? i===currentAngle : i===index) ? ' active' : '');
        d.addEventListener('click', () => {
          if (showingAngles) {
            currentAngle = i;
          } else {
            index = i;
          }
          showingAngles = false;
          updateImage();
        });
        dotContainer.appendChild(d);
      });
  }

  function updateImage() {
    if (!viewerImg) return;
    viewerImg.classList.add('animate');
    setTimeout(() => {
      const imageSet    = showingAngles ? currentSet.angles : currentSet.skins;
      const currentIndex= showingAngles ? currentAngle : index;
      viewerImg.src     = imageSet[currentIndex];
      if (lightbox && lightbox.classList.contains('active')) lightboxImg.src = imageSet[currentIndex];
      viewerImg.onload = () => viewerImg.classList.remove('animate');

      if (showingAngles) {
        if (currentCaption) currentCaption.textContent = nameSet[0] + ' – Angle ' + (currentAngle + 1);
        if (imageCount)     imageCount.textContent    = (currentAngle + 1) + ' of 4';
      } else {
        if (currentCaption) currentCaption.textContent = nameSet[index];
        if (imageCount)     imageCount.textContent    = (index + 1) + ' of ' + currentSet.skins.length;
        if (currentName)    currentName.textContent   = nameSet[index];
        if (prevName)       prevName.textContent      = nameSet[(index - 1 + nameSet.length) % nameSet.length];
        if (nextName)       nextName.textContent      = nameSet[(index + 1) % nameSet.length];
      }
      buildDots();
    }, 100);
  }

  // Carousel & angle buttons
  prevBtn     && prevBtn.addEventListener('click', () => { index = (index - 1 + currentSet.skins.length) % currentSet.skins.length; showingAngles = false; updateImage(); });
  nextBtn     && nextBtn.addEventListener('click', () => { index = (index + 1) % currentSet.skins.length; showingAngles = false; updateImage(); });
  angleLeftBtn&& angleLeftBtn.addEventListener('click', () => { currentAngle = (currentAngle - 1 + 4) % 4; showingAngles = true; updateImage(); });
  angleRightBtn&& angleRightBtn.addEventListener('click', () => { currentAngle = (currentAngle + 1) % 4; showingAngles = true; updateImage(); });
  prevName    && prevName.addEventListener('click', () => prevBtn.click());
  currentName && currentName.addEventListener('click', updateImage);
  nextName    && nextName.addEventListener('click', () => nextBtn.click());

  // Variant switch
  document.querySelectorAll('input[name="glove"]').forEach(radio => {
    radio.addEventListener('change', () => {
      if (!radio.checked) return;
      currentGlove = radio.value;
      currentSet   = urls[currentGlove];
      nameSet      = gloves[currentGlove];
      index        = 0;
      currentAngle = 0;
      showingAngles= false;
      updateImage();
      document.querySelector('.glove-column').classList.remove('pandora','vice','hedge');
      document.querySelector('.glove-column').classList.add(currentGlove);
    });
  });

  // Preorder buttons (simulate add to cart)
  var preorderBtn = document.querySelector('.btn-preorder');
  var cryptoBtn = document.querySelector('.btn-crypto');
  if (preorderBtn) {
    preorderBtn.addEventListener('click', function() {
      var glove = document.querySelector('input[name="glove"]:checked').value;
      var qtyBtn = document.querySelector('.quantity-btn.active');
      var qty = qtyBtn ? parseInt(qtyBtn.textContent) : 1;
      alert('Pre-order: ' + glove + ' x' + qty + ' (simulate add to cart)');
    });
  }
  if (cryptoBtn) {
    cryptoBtn.addEventListener('click', function() {
      alert('Redirect to crypto payment (simulate)');
    });
  }

  // Init gallery
  updateImage();
  buildDots();

  // Product image gallery thumbs
  const thumbs = document.querySelectorAll('.gallery-thumb');
  const mainImg = document.getElementById('viewer-img');
  if (thumbs.length && mainImg) {
    thumbs.forEach((thumb, i) => {
      thumb.addEventListener('click', function() {
        thumbs.forEach(t => t.classList.remove('selected'));
        thumb.classList.add('selected');
        mainImg.src = thumb.getAttribute('data-img');
      });
      if (i === 0) thumb.classList.add('selected');
    });
  }
});
