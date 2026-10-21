const OrbitTheme=Object.freeze({
 tokens:{accent:'#6A1833',secondary:'#D44769',paper:'#101010',ink:'#F4F4F4',lightAction:'#6A1833',surface:'#303030'},
 color(value){const map={'#17d4c0':'#6A1833','#8cf6ea':'#D44769','#010e0d':'#101010','#0b302e':'#303030','#eafffc':'#F4F4F4','#0e9f92':'#6A1833','#921b37':'#6A1833','#b72b51':'#6A1833','#d44769':'#D44769','#e64570':'#6A1833','#651426':'#6A1833','#101010':'#101010','#181818':'#101010','#252525':'#303030','#303030':'#303030','#f4f4f4':'#F4F4F4'};return map[String(value).toLowerCase()]||value},
 brand(value){return ['GuardianChat','Guardian Chat','X ORBIT','ORBIT'].includes(value)?'X ORBIT':value},
 chat(value){return ['GuardianChat','Guardian Chat','X ORBIT','ORBIT'].includes(value)?'Orbit Chat':value},
 gaming(value){return ['Gamebox','GameBox','Clutch Naija'].includes(value)?'OrbitPlay':value}
});
