// Lazy-start below-the-fold videos; the hero video autoplays. Promotion-tree stepper.
(function(){
  var vids=document.querySelectorAll('video[data-lazy]');
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      var v=e.target;
      if(e.isIntersecting){ if(!v.dataset.loaded){v.preload='auto';v.dataset.loaded=1;} if(!reduce){var p=v.play();if(p&&p.catch)p.catch(function(){});} }
      else v.pause();
    });},{rootMargin:'200px',threshold:.15});
    vids.forEach(function(v){io.observe(v);});
  }else{vids.forEach(function(v){v.controls=true;});}
  var st=document.getElementById('stepper'); if(!st)return;
  var steps=JSON.parse(st.getAttribute('data-steps')),i=0,timer=null;
  var img=st.querySelector('img'),cap=st.querySelector('.cap'),dots=st.querySelector('.dots'),play=st.querySelector('.play');
  steps.forEach(function(s,k){var b=document.createElement('button');b.textContent=String(k+1);b.setAttribute('aria-label','Step '+(k+1)+': '+s.t);b.onclick=function(){stop();show(k);};dots.appendChild(b);});
  function show(k){i=k;img.src=s_(k).src;img.alt=s_(k).alt;cap.innerHTML='<b>'+(k+1)+'. '+s_(k).t+'</b> '+s_(k).d;
    Array.prototype.forEach.call(dots.children,function(b,j){b.classList.toggle('on',j===k);});}
  function s_(k){return steps[k];}
  function next(){show((i+1)%steps.length);}
  function go(){timer=setInterval(next,3200);play.textContent='Pause';play.setAttribute('aria-pressed','true');}
  function stop(){clearInterval(timer);timer=null;play.textContent='Play';play.setAttribute('aria-pressed','false');}
  play.onclick=function(){timer?stop():go();};
  steps.forEach(function(s){var im=new Image();im.src=s.src;});
  show(0); if(!reduce) go();
})();
// theme toggle (default: dark, or the OS light preference; choice kept in localStorage if available)
(function(){
  var b=document.getElementById('theme-toggle'),l=document.getElementById('theme-label');if(!b)return;
  var root=document.documentElement;
  function isLight(){var t=root.getAttribute('data-theme');return t?t==='light':(window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches);}
  function sync(){var x=isLight();b.setAttribute('aria-checked',x?'true':'false');l.textContent=x?'Light mode':'Light mode';}
  b.onclick=function(){var t=isLight()?'dark':'light';root.setAttribute('data-theme',t);try{localStorage.setItem('savior-theme',t);}catch(e){}sync();};
  sync();
})();
