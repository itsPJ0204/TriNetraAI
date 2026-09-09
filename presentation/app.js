// Interactive Slide Presentation State & Controller
let currentSlide = 1;
const totalSlides = 4;

const nodeDetails = {
  tiling_grid: {
    title: "🗺️ Layer 1: Spatial Indexing & Tiling (Role 1)",
    badge: "Data Engineering / The Librarian",
    role: "Person 1 (Huzaifa)",
    desc: "Transforms multi-gigabyte satellite scenes into rapid-access co-registered 512x512 patches with geospatial metadata.",
    points: [
      "Rasterio-based geographic CRS alignment across UTM and EPSG:4326 projections.",
      "Calculates multi-temporal geographic bounding box intersections and patch grid slicing.",
      "Maintains geospatial metadata schema in SQLite (bounds, resolution, acquisition timestamps)."
    ]
  },
  semantic_search: {
    title: "🔍 Layer 2: RemoteCLIP Vector Search (Role 2)",
    badge: "Semantic AI / The Translator",
    role: "Person 2 (Rahim)",
    desc: "Enables zero-shot natural language retrieval across satellite archives without coordinate inputs.",
    points: [
      "RemoteCLIP (ViT-B/32) vision-language encoder trained on earth observation imagery.",
      "512-dimensional L2-normalized vector embeddings indexed in Qdrant Vector DB.",
      "Achieves 0.9333 MRR and 86.7% Top-1 Accuracy on satellite semantic benchmarks."
    ]
  },
  qa_filter: {
    title: "🛡️ Layer 3: Just-In-Time QA False-Alarm Suppression (Role 4)",
    badge: "Quality Assurance & JIT Suppression",
    role: "Person 4 (Piyush)",
    desc: "Applied Just-In-Time (JIT) directly at the input of Temporal Change Detection to eliminate environmental false positives efficiently.",
    points: [
      "On-Demand SCL Filtering: Runs specifically on queried bitemporal tile pairs (t1, t2) rather than wasting CPU cycles on millions of raw ingested tiles upfront.",
      "Suppresses Scene Classification Layer (SCL) Class 3 (Shadows), Classes 8/9/10 (Clouds), and Class 11 (Snow/Ice).",
      "Morphological binary halo erosion (2-pixel kernel) removing cloud boundary edge artifacts.",
      "Offline s2cloudless gradient-boosted decision trees running on edge hardware."
    ]
  },
  temporal_detective: {
    title: "🕵️‍♂️ Layer 4: Temporal Change Detective & Classifier (Role 3)",
    badge: "Temporal AI / The Detective",
    role: "Person 3 (Krishna)",
    desc: "Detects WHERE change occurred on QA-verified pixels and classifies WHAT transitioned.",
    points: [
      "Dual-Engine: Deep Learning Bitemporal Image Transformer (BIT) + High-Speed Classical Gaussian Diff fallback.",
      "Applies Bitemporal Intersection: Clean Change = Raw BIT Change ∩ QA(t1) ∩ QA(t2).",
      "Zero-Shot Semantic Transition Matrix (e.g., Vegetation -> Construction, Open Land -> Road).",
      "Automated morphological cleaning, sub-pixel contour bounding boxes, and 40% red overlay generation."
    ]
  },
  frontend_hub: {
    title: "🖥️ Layer 5: Analyst Command Dashboard (Role 5)",
    badge: "Frontend Lead / The Storefront",
    role: "Person 5",
    desc: "Interactive Leaflet.js map client and human-in-the-loop verification review queue.",
    points: [
      "Unified FastAPI backend endpoints (/api/search, /api/changes, /api/similar).",
      "Interactive Before/After visual split slider with polygon bounding box overlays.",
      "One-click Approve/Reject audit log satisfying intelligence provenance requirements."
    ]
  }
};

function goToSlide(slideIndex) {
  if (slideIndex < 1 || slideIndex > totalSlides) return;
  
  // Hide all slides
  document.querySelectorAll('.slide').forEach(slide => {
    slide.classList.remove('active');
  });
  
  // Deactivate all tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Activate target slide
  const targetSlide = document.getElementById(`slide-${slideIndex}`);
  if (targetSlide) {
    targetSlide.classList.add('active');
  }
  
  // Activate tab
  const targetTab = document.querySelector(`.tab-btn[data-slide="${slideIndex}"]`);
  if (targetTab) {
    targetTab.classList.add('active');
  }
  
  currentSlide = slideIndex;
  
  // Update Prev/Next buttons
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  if (prevBtn) prevBtn.disabled = currentSlide === 1;
  if (nextBtn) nextBtn.disabled = currentSlide === totalSlides;
}

function showNodeModal(nodeKey) {
  const data = nodeDetails[nodeKey];
  if (!data) return;
  
  const modal = document.getElementById('info-modal');
  const title = document.getElementById('modal-title');
  const badge = document.getElementById('modal-badge');
  const desc = document.getElementById('modal-desc');
  const list = document.getElementById('modal-list');
  
  title.innerText = data.title;
  badge.innerText = data.badge;
  desc.innerText = data.desc;
  
  list.innerHTML = '';
  data.points.forEach(pt => {
    const li = document.createElement('li');
    li.style.marginBottom = '8px';
    li.style.lineHeight = '1.45';
    li.innerText = pt;
    list.appendChild(li);
  });
  
  modal.classList.add('open');
}

function closeModal() {
  const modal = document.getElementById('info-modal');
  if (modal) modal.classList.remove('open');
}

function toggleFullScreen() {
  const elem = document.querySelector('.presentation-viewport');
  if (!document.fullscreenElement) {
    elem.requestFullscreen().catch(err => {
      alert(`Error attempting to enable fullscreen: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Tab clicks
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(e.target.getAttribute('data-slide'));
      goToSlide(idx);
    });
  });
  
  // Arrow buttons
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  if (prevBtn) prevBtn.addEventListener('click', () => goToSlide(currentSlide - 1));
  if (nextBtn) nextBtn.addEventListener('click', () => goToSlide(currentSlide + 1));
  
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === 'Space') {
      goToSlide(currentSlide + 1);
    } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
      goToSlide(currentSlide - 1);
    } else if (e.key === 'Escape') {
      closeModal();
    }
  });
  
  // Fullscreen button
  const fsBtn = document.getElementById('fs-btn');
  if (fsBtn) fsBtn.addEventListener('click', toggleFullScreen);
  
  // Print / PDF export
  const printBtn = document.getElementById('print-btn');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }
});
