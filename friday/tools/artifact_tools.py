"""
Artifact generation tools — interactive HTML content (games, websites, SVGs,
animations, documents) that can be previewed in a browser.

This is FRIDAY's equivalent of "Claude Artifacts".
"""
from __future__ import annotations

import json
import os
import re
import uuid
import webbrowser
from datetime import datetime, timezone
from typing import Any

from friday.logging_utils import configure_logging
from friday._paths import FRIDAY_MEMORY

logger = configure_logging("artifact_tools")
ARTIFACT_DIR = os.path.join(FRIDAY_MEMORY, "artifacts")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-_")


def _wrap_html(title: str, body: str, css: str = "", js: str = "") -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>__TITLE__</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
__CSS__
</style>
</head>
<body>
__BODY__
<script>
__JS__
</script>
</body>
</html>""".replace("__TITLE__", title).replace("__BODY__", body).replace("__CSS__", css).replace("__JS__", js)


def _save_artifact(html: str, title: str, artifact_type: str, extra: dict | None = None) -> dict:
    slug = _slugify(title) or "artifact"
    artifact_id = str(uuid.uuid4())[:8]
    folder = os.path.join(ARTIFACT_DIR, f"{slug}-{artifact_id}")
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "index.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{os.path.abspath(file_path)}")
    result: dict[str, Any] = {
        "success": True,
        "file_path": file_path,
        "artifact_id": artifact_id,
        "title": title,
        "type": artifact_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        result.update(extra)
    return result


# ---------------------------------------------------------------------------
# Game templates  (complete standalone HTML5 games)
# ---------------------------------------------------------------------------

_SLIDING_PUZZLE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sliding Puzzle</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;color:#fff}
.container{text-align:center}
h1{margin-bottom:20px;color:#e94560}
.puzzle-grid{display:grid;grid-template-columns:repeat(4,80px);gap:4px;background:#16213e;padding:8px;border-radius:8px;margin:0 auto;width:344px}
.tile{width:80px;height:80px;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:bold;background:#0f3460;border-radius:4px;cursor:pointer;transition:all .2s;user-select:none}
.tile:hover{background:#1a5276}
.tile.empty{background:transparent;cursor:default;pointer-events:none}
.tile.correct{background:#2d6a4f;color:#fff}
.info{margin-top:20px;font-size:18px}
button{padding:10px 24px;font-size:16px;background:#e94560;color:#fff;border:none;border-radius:4px;cursor:pointer;margin:10px 4px}
button:hover{background:#c73e54}
select{padding:10px;font-size:16px;border-radius:4px;border:none;background:#0f3460;color:#fff;margin:10px 4px}
.counter{color:#e94560;font-weight:bold}
</style>
</head>
<body>
<div class="container">
<h1>Sliding Puzzle</h1>
<div style="margin-bottom:10px">
<select id="sizeSelect"><option value="3">3x3</option><option value="4" selected>4x4</option><option value="5">5x5</option></select>
<button onclick="changeSize()">Set Size</button>
</div>
<div class="puzzle-grid" id="grid"></div>
<div class="info">
Moves: <span class="counter" id="moves">0</span>
</div>
<button onclick="initGame()">New Game</button>
<div id="winMsg" style="margin-top:10px;font-size:20px;color:#4ecca3;display:none"></div>
</div>
<script>
let tiles=[],emptyIndex=0,gridSize=4,totalTiles=16,moves=0,gameWon=false;
function changeSize(){
  gridSize=parseInt(document.getElementById('sizeSelect').value);
  totalTiles=gridSize*gridSize;
  initGame();
}
function initGame(){
  tiles=[...Array(totalTiles).keys()];
  emptyIndex=totalTiles-1;
  moves=0;gameWon=false;
  document.getElementById('moves').textContent='0';
  document.getElementById('winMsg').style.display='none';
  do{shuffle(tiles)}while(!isSolvable(tiles)||isSolved(tiles));
  render();
}
function shuffle(a){for(let i=a.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}emptyIndex=a.indexOf(totalTiles-1);}
function isSolvable(a){
  let inv=0;
  for(let i=0;i<totalTiles;i++)for(let j=i+1;j<totalTiles;j++)if(a[i]!==totalTiles-1&&a[j]!==totalTiles-1&&a[i]>a[j])inv++;
  if(gridSize%2===0){let rowFromBottom=gridSize-Math.floor(a.indexOf(totalTiles-1)/gridSize);return rowFromBottom%2!==inv%2;}
  return inv%2===0;
}
function isSolved(a){return a.every((v,i)=>v===i)}
function canMove(idx){
  let ei=emptyIndex,ix=idx%gridSize,iy=Math.floor(idx/gridSize),ex=ei%gridSize,ey=Math.floor(ei/gridSize);
  return (Math.abs(ix-ex)+Math.abs(iy-ey))===1;
}
function moveTile(idx){
  if(gameWon||!canMove(idx))return;
  tiles[emptyIndex]=tiles[idx];
  tiles[idx]=totalTiles-1;
  emptyIndex=idx;
  moves++;
  document.getElementById('moves').textContent=moves;
  render();
  if(isSolved(tiles)){gameWon=true;document.getElementById('winMsg').textContent='You solved it in '+moves+' moves!';document.getElementById('winMsg').style.display='block';}
}
function render(){
  let grid=document.getElementById('grid');
  grid.style.gridTemplateColumns='repeat('+gridSize+',80px)';
  grid.innerHTML='';
  tiles.forEach((v,i)=>{
    let div=document.createElement('div');
    div.className='tile'+(v===totalTiles-1?' empty':'');
    if(v!==totalTiles-1)div.textContent=v+1;
    div.onclick=()=>moveTile(i);
    grid.appendChild(div);
  });
}
initGame();
</script>
</body>
</html>"""


_SNAKE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Snake Game</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;color:#fff}
.container{text-align:center}
canvas{border:2px solid #16213e;border-radius:4px;background:#16213e;display:block;margin:10px auto}
.info{font-size:18px;margin:8px 0}
.info span{color:#e94560;font-weight:bold}
.over{color:#e94560;font-size:22px;margin-top:10px;display:none}
button{padding:10px 24px;font-size:16px;background:#e94560;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}
button:hover{background:#c73e54}
.hint{color:#888;font-size:14px;margin-top:6px}
</style>
</head>
<body>
<div class="container">
<h1 style="color:#4ecca3">Snake</h1>
<div class="info">Score: <span id="score">0</span> | High: <span id="high">0</span></div>
<canvas id="game" width="400" height="400"></canvas>
<div class="over" id="over">Game Over! Score: <span id="final"></span></div>
<button onclick="init()">New Game</button>
<div class="hint">Arrow keys to move | Enter/Space to restart</div>
</div>
<script>
const canvas=document.getElementById('game'),ctx=canvas.getContext('2d');
const S=20,N=20;
let snake,food,dir,nextDir,score,high,gameOver,loop;
function init(){
  snake=[{x:10,y:10}];dir={x:0,y:0};nextDir={x:0,y:0};score=0;gameOver=false;
  document.getElementById('score').textContent='0';document.getElementById('over').style.display='none';
  placeFood();if(loop)clearInterval(loop);loop=setInterval(tick,120);
}
function placeFood(){
  do{food={x:Math.floor(Math.random()*N),y:Math.floor(Math.random()*N)}}
  while(snake.some(p=>p.x===food.x&&p.y===food.y));
}
function tick(){
  if(gameOver)return;
  dir={x:nextDir.x,y:nextDir.y};
  if(dir.x===0&&dir.y===0)return;
  let head={x:snake[0].x+dir.x,y:snake[0].y+dir.y};
  if(head.x<0||head.x>=N||head.y<0||head.y>=N||snake.some(p=>p.x===head.x&&p.y===head.y)){endGame();return;}
  snake.unshift(head);
  if(head.x===food.x&&head.y===food.y){score++;document.getElementById('score').textContent=score;placeFood();}
  else snake.pop();
  draw();
}
function endGame(){gameOver=true;clearInterval(loop);
  if(score>high){high=score;document.getElementById('high').textContent=high;}
  document.getElementById('final').textContent=score;document.getElementById('over').style.display='block';
}
function draw(){
  ctx.fillStyle='#16213e';ctx.fillRect(0,0,400,400);
  for(let i=0;i<N;i++)for(let j=0;j<N;j++){ctx.fillStyle=(i+j)%2===0?'#1a1a2e':'#16213e';ctx.fillRect(i*S,j*S,S,S);}
  ctx.fillStyle='#e94560';ctx.beginPath();ctx.arc(food.x*S+S/2,food.y*S+S/2,S/2-2,0,Math.PI*2);ctx.fill();
  snake.forEach((p,i)=>{ctx.fillStyle=i===0?'#4ecca3':'#2d6a4f';ctx.fillRect(p.x*S+1,p.y*S+1,S-2,S-2);});
}
document.addEventListener('keydown',e=>{
  if(gameOver&&(e.key==='Enter'||e.key===' ')){init();return;}
  const k=e.key.replace('Arrow','');
  if(k==='Up'&&dir.y!==1)nextDir={x:0,y:-1};
  else if(k==='Down'&&dir.y!==-1)nextDir={x:0,y:1};
  else if(k==='Left'&&dir.x!==1)nextDir={x:-1,y:0};
  else if(k==='Right'&&dir.x!==-1)nextDir={x:1,y:0};
});
init();
</script>
</body>
</html>"""


_BREAKOUT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Breakout</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;color:#fff}
.container{text-align:center}
canvas{border:2px solid #0f3460;border-radius:4px;background:#16213e;display:block;margin:10px auto}
.info{font-size:18px;margin:6px 0}
.info span{color:#e94560;font-weight:bold}
.lives span{color:#4ecca3}
.msg{color:#e94560;font-size:22px;margin-top:8px;display:none}
button{padding:10px 24px;font-size:16px;background:#e94560;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}
button:hover{background:#c73e54}
</style>
</head>
<body>
<div class="container">
<h1 style="color:#e94560">Breakout</h1>
<div class="info">Score: <span id="score">0</span> | <span class="lives">Lives: <span id="lives">3</span></span></div>
<canvas id="game" width="640" height="420"></canvas>
<div class="msg" id="msg"></div>
<button onclick="init()">New Game</button>
</div>
<script>
const canvas=document.getElementById('game'),ctx=canvas.getContext('2d');
const W=640,H=420;
let paddle,ball,bricks,score,lives,gameOver,win,anim;
const PW=90,PH=12,BR=7,R=5;
const COLS=10,ROWS=6,BW=54,BH=18,BP=4;
const TOP=40,LEFT=(W-(COLS*(BW+BP)))/2;
const COLORS=['#e94560','#e94560','#f5a623','#f5a623','#4ecca3','#4ecca3','#0f3460','#0f3460','#16213e','#16213e'];
function init(){
  paddle={x:W/2-PW/2,y:H-40,w:PW,h:PH};
  ball={x:W/2,y:H-55,r:BR,dx:3,dy:-4};
  bricks=[];
  for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++)bricks.push({x:LEFT+c*(BW+BP),y:TOP+r*(BH+BP),w:BW,h:BH,a:true,cl:COLORS[r]});
  score=0;lives=3;gameOver=false;win=false;
  document.getElementById('score').textContent='0';document.getElementById('lives').textContent='3';document.getElementById('msg').style.display='none';
  if(anim)cancelAnimationFrame(anim);loop();
}
function loop(){
  update();draw();
  if(!gameOver&&!win)anim=requestAnimationFrame(loop);
}
function update(){
  ball.x+=ball.dx;ball.y+=ball.dy;
  if(ball.x-R<0||ball.x+R>W){ball.dx=-ball.dx;ball.x=Math.max(R,Math.min(W-R,ball.x));}
  if(ball.y-R<0){ball.dy=-ball.dy;ball.y=R;}
  if(ball.y+R>H){lives--;document.getElementById('lives').textContent=lives;if(lives<=0){showMsg('Game Over!');gameOver=true;return;}resetBall();return;}
  if(ball.y+R>paddle.y&&ball.y-R<paddle.y+paddle.h&&ball.x>paddle.x&&ball.x<paddle.x+paddle.w){
    let hit=Math.max(-1,Math.min(1,(ball.x-(paddle.x+paddle.w/2))/(paddle.w/2)));
    let angle=hit*Math.PI/3;let sp=Math.sqrt(ball.dx*ball.dx+ball.dy*ball.dy);
    ball.dx=sp*Math.sin(angle);ball.dy=-sp*Math.cos(angle);ball.y=paddle.y-R;
  }
  for(let b of bricks){
    if(!b.a)continue;
    if(ball.x+R>b.x&&ball.x-R<b.x+b.w&&ball.y+R>b.y&&ball.y-R<b.y+b.h){
      b.a=false;score+=10;document.getElementById('score').textContent=score;
      let ox=Math.min(ball.x+R-b.x,b.x+b.w-(ball.x-R));
      let oy=Math.min(ball.y+R-b.y,b.y+b.h-(ball.y-R));
      if(ox<oy)ball.dx=-ball.dx;else ball.dy=-ball.dy;
      if(bricks.every(x=>!x.a)){showMsg('You Win!');win=true;}
      break;
    }
  }
}
function resetBall(){ball.x=W/2;ball.y=H-55;ball.dx=3;ball.dy=-4;}
function showMsg(t){document.getElementById('msg').textContent=t;document.getElementById('msg').style.display='block';}
function draw(){
  ctx.fillStyle='#16213e';ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#0f3460';ctx.beginPath();ctx.roundRect(paddle.x,paddle.y,paddle.w,paddle.h,4);ctx.fill();
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(ball.x,ball.y,R,0,Math.PI*2);ctx.fill();
  for(let b of bricks){if(!b.a)continue;ctx.fillStyle=b.cl;ctx.fillRect(b.x,b.y,b.w,b.h);}
}
canvas.addEventListener('mousemove',e=>{
  let r=canvas.getBoundingClientRect();let x=e.clientX-r.left;
  paddle.x=Math.max(0,Math.min(W-paddle.w,x));
});
init();
</script>
</body>
</html>"""


_TETRIS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tetris</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;color:#fff}
.game-wrapper{display:flex;gap:20px;align-items:flex-start}
.main{text-align:center}
canvas{border:2px solid #0f3460;border-radius:4px;background:#16213e;display:block}
.side{text-align:center}
.side h3{color:#e94560;margin-bottom:8px}
.info{margin:8px 0;font-size:16px}
.info span{color:#e94560;font-weight:bold}
button{padding:10px 24px;font-size:16px;background:#e94560;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}
button:hover{background:#c73e54}
.hint{color:#888;font-size:13px;margin-top:6px}
</style>
</head>
<body>
<div class="game-wrapper">
<div class="main">
<canvas id="board" width="300" height="600"></canvas>
<div class="info">Score: <span id="score">0</span> | Level: <span id="level">1</span> | Lines: <span id="lines">0</span></div>
<button onclick="init()">New Game</button>
<div class="hint">&larr;&rarr; Move &uarr; Rotate &darr; Soft Drop Space: Hard Drop</div>
</div>
<div class="side">
<h3>Next</h3>
<canvas id="next" width="120" height="120"></canvas>
</div>
</div>
<script>
const CO=10,RO=20,BS=30;
const bc=document.getElementById('board'),bx=bc.getContext('2d');
const nc=document.getElementById('next'),nx=nc.getContext('2d');
bc.width=CO*BS;bc.height=RO*BS;nc.width=120;nc.height=120;
const PIECES=[
  {s:[[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],c:'#00f0f0'},
  {s:[[1,1],[1,1]],c:'#f0f000'},
  {s:[[0,1,0],[1,1,1],[0,0,0]],c:'#a000f0'},
  {s:[[0,1,1],[1,1,0],[0,0,0]],c:'#00f000'},
  {s:[[1,1,0],[0,1,1],[0,0,0]],c:'#f00000'},
  {s:[[1,0,0],[1,1,1],[0,0,0]],c:'#0000f0'},
  {s:[[0,0,1],[1,1,1],[0,0,0]],c:'#f0a000'}
];
let board,cur,next,score,level,lines,gameOver,dropDelay,gLoop;
function emptyBoard(){return Array.from({length:RO},()=>Array(CO).fill(0));}
function randPiece(){let p=PIECES[Math.floor(Math.random()*PIECES.length)];return{s:p.s.map(r=>[...r]),c:p.c};}
function init(){
  board=emptyBoard();next=randPiece();score=0;level=1;lines=0;gameOver=false;dropDelay=500;
  document.getElementById('score').textContent='0';document.getElementById('level').textContent='1';document.getElementById('lines').textContent='0';
  spawn();if(gLoop)clearInterval(gLoop);gLoop=setInterval(()=>{if(!gameOver){drop();draw();}},dropDelay);draw();
}
function spawn(){
  cur=next;next=randPiece();
  cur.x=Math.floor((CO-cur.s[0].length)/2);cur.y=0;
  if(collides(cur.s,cur.x,cur.y)){gameOver=true;clearInterval(gLoop);draw();}
}
function collides(s,x,y){for(let r=0;r<s.length;r++)for(let c=0;c<s[r].length;c++){if(!s[r][c])continue;let bx=x+c,by=y+r;if(bx<0||bx>=CO||by>=RO)return true;if(by>=0&&board[by][bx])return true;}return false;}
function rotate(s){let N=s.length;let r=Array.from({length:N},()=>Array(N).fill(0));for(let i=0;i<N;i++)for(let j=0;j<N;j++)r[j][N-1-i]=s[i][j];return r;}
function move(dx,dy){
  if(!cur||gameOver)return;
  if(!collides(cur.s,cur.x+dx,cur.y+dy)){cur.x+=dx;cur.y+=dy;draw();}
  else if(dy>0){lock();}
}
function rotatePiece(){
  if(!cur||gameOver)return;let r=rotate(cur.s);
  if(!collides(r,cur.x,cur.y))cur.s=r;
  else if(!collides(r,cur.x-1,cur.y)){cur.s=r;cur.x--;}
  else if(!collides(r,cur.x+1,cur.y)){cur.s=r;cur.x++;}
  draw();
}
function drop(){if(cur&&!gameOver&&!collides(cur.s,cur.x,cur.y+1)){cur.y++;draw();}else lock();}
function hardDrop(){if(!cur||gameOver)return;while(!collides(cur.s,cur.x,cur.y+1))cur.y++;lock();draw();}
function lock(){
  for(let r=0;r<cur.s.length;r++)for(let c=0;c<cur.s[r].length;c++){if(cur.s[r][c]){let by=cur.y+r,bx=cur.x+c;if(by>=0)board[by][bx]=cur.c;}}
  clearLines();spawn();draw();
}
function clearLines(){
  let cl=0;
  for(let r=RO-1;r>=0;r--){if(board[r].every(c=>c!==0)){board.splice(r,1);board.unshift(Array(CO).fill(0));cl++;r++;}}
  if(cl>0){lines+=cl;let pts=[0,100,300,500,800];score+=pts[Math.min(cl,4)]*level;level=Math.floor(lines/10)+1;dropDelay=Math.max(80,500-(level-1)*35);
    document.getElementById('score').textContent=score;document.getElementById('level').textContent=level;document.getElementById('lines').textContent=lines;
    clearInterval(gLoop);gLoop=setInterval(()=>{if(!gameOver){drop();draw();}},dropDelay);}
}
function draw(){
  bx.fillStyle='#16213e';bx.fillRect(0,0,bc.width,bc.height);
  for(let r=0;r<RO;r++)for(let c=0;c<CO;c++){if(board[r][c]){bx.fillStyle=board[r][c];bx.fillRect(c*BS,r*BS,BS-1,BS-1);}}
  if(cur){for(let r=0;r<cur.s.length;r++)for(let c=0;c<cur.s[r].length;c++){if(cur.s[r][c]){bx.fillStyle=cur.c;bx.fillRect((cur.x+c)*BS,(cur.y+r)*BS,BS-1,BS-1);}}}
  bx.strokeStyle='#0f3460';bx.lineWidth=0.5;
  for(let r=1;r<RO;r++){bx.beginPath();bx.moveTo(0,r*BS);bx.lineTo(bc.width,r*BS);bx.stroke();}
  for(let c=1;c<CO;c++){bx.beginPath();bx.moveTo(c*BS,0);bx.lineTo(c*BS,bc.height);bx.stroke();}
  nx.fillStyle='#1a1a2e';nx.fillRect(0,0,120,120);
  if(next){let s=next.s[0].length>2?22:28;let ox=(120-s*next.s[0].length)/2,oy=(120-s*next.s.length)/2;
    for(let r=0;r<next.s.length;r++)for(let c=0;c<next.s[r].length;c++){if(next.s[r][c]){nx.fillStyle=next.c;nx.fillRect(ox+c*s,oy+r*s,s-1,s-1);}}}
}
document.addEventListener('keydown',e=>{
  if(gameOver&&(e.key==='Enter'||e.key===' ')){init();return;}
  if(e.key==='ArrowLeft')move(-1,0);
  else if(e.key==='ArrowRight')move(1,0);
  else if(e.key==='ArrowDown')move(0,1);
  else if(e.key==='ArrowUp')rotatePiece();
  else if(e.key===' ')hardDrop();
});
init();
</script>
</body>
</html>"""


_TRIVIA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Trivia Quiz</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;color:#fff}
.container{text-align:center;max-width:600px;width:100%}
h1{color:#e94560;margin-bottom:20px}
.card{background:#16213e;border-radius:12px;padding:30px;margin:10px 0;min-height:200px}
.category{color:#4ecca3;font-size:14px;text-transform:uppercase;margin-bottom:10px}
.question{font-size:20px;line-height:1.5;margin-bottom:20px}
.options{display:flex;flex-direction:column;gap:10px}
.option{background:#0f3460;border:2px solid transparent;padding:14px 20px;border-radius:8px;cursor:pointer;font-size:16px;text-align:left;transition:all .2s}
.option:hover{border-color:#4ecca3;background:#1a5276}
.option.selected{border-color:#4ecca3}
.option.correct{background:#2d6a4f;border-color:#4ecca3}
.option.wrong{background:#6b2d2d;border-color:#e94560}
.option.disabled{pointer-events:none;opacity:.7}
.footer{display:flex;justify-content:space-between;align-items:center;margin-top:20px}
.score{font-size:18px}
.score span{color:#e94560;font-weight:bold}
button{padding:12px 28px;font-size:16px;background:#e94560;color:#fff;border:none;border-radius:8px;cursor:pointer}
button:hover{background:#c73e54}
button:disabled{opacity:.4;cursor:default}
.progress{color:#888;font-size:14px;margin-top:10px}
</style>
</head>
<body>
<div class="container">
<h1>Trivia Quiz</h1>
<div class="card">
<div class="category" id="category">General</div>
<div class="question" id="question">Loading...</div>
<div class="options" id="options"></div>
</div>
<div class="footer">
<div class="score">Score: <span id="score">0</span>/<span id="total">0</span></div>
<button id="nextBtn" onclick="nextQuestion()" disabled>Next</button>
</div>
<div class="progress" id="progress">Question 1 of 10</div>
</div>
<script>
const QUESTIONS=[
  {q:"What planet is known as the Red Planet?",o:["Venus","Mars","Jupiter","Saturn"],a:1,c:"Astronomy"},
  {q:"What is 2+2?",o:["3","4","5","6"],a:1,c:"Math"},
  {q:"Who painted the Mona Lisa?",o:["Michelangelo","Da Vinci","Raphael","Donatello"],a:1,c:"Art"},
  {q:"What is the capital of France?",o:["London","Berlin","Paris","Madrid"],a:2,c:"Geography"},
  {q:"Which animal is known as the King of the Jungle?",o:["Tiger","Bear","Lion","Elephant"],a:2,c:"Animals"},
  {q:"What year did World War II end?",o:["1943","1944","1945","1946"],a:2,c:"History"},
  {q:"What is the largest ocean on Earth?",o:["Atlantic","Indian","Arctic","Pacific"],a:3,c:"Geography"},
  {q:"Which element has the symbol 'O'?",o:["Gold","Oxygen","Silver","Iron"],a:1,c:"Science"},
  {q:"How many strings does a standard guitar have?",o:["4","5","6","7"],a:2,c:"Music"},
  {q:"What is the speed of light approximately?",o:["300,000 km/s","150,000 km/s","500,000 km/s","100,000 km/s"],a:0,c:"Science"}
];
let idx=0,score=0,answered=false,shuffled=[];
function shuffle(a){for(let i=a.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function initQuiz(){shuffled=shuffle([...Array(QUESTIONS.length).keys()]);idx=0;score=0;render();}
function render(){
  if(idx>=shuffled.length){showResults();return;}
  let q=QUESTIONS[shuffled[idx]];answered=false;
  document.getElementById('category').textContent=q.c;
  document.getElementById('question').textContent=q.q;
  document.getElementById('progress').textContent='Question '+(idx+1)+' of '+shuffled.length;
  document.getElementById('total').textContent=score;
  document.getElementById('nextBtn').disabled=true;
  let opts=document.getElementById('options');opts.innerHTML='';
  q.o.forEach((text,i)=>{
    let div=document.createElement('div');div.className='option';div.textContent=(i+1)+'. '+text;
    div.onclick=()=>selectAnswer(i);opts.appendChild(div);
  });
}
function selectAnswer(i){
  if(answered)return;answered=true;
  let q=QUESTIONS[shuffled[idx]];let opts=document.querySelectorAll('.option');
  opts.forEach((el,j)=>{el.classList.add('disabled');if(j===q.a)el.classList.add('correct');if(j===i&&j!==q.a)el.classList.add('wrong');});
  if(i===q.a)score++;
  document.getElementById('score').textContent=score;
  document.getElementById('nextBtn').disabled=false;
}
function nextQuestion(){idx++;render();}
function showResults(){
  document.getElementById('category').textContent='Complete!';
  document.getElementById('question').textContent='You scored '+score+' out of '+shuffled.length+'!';
  document.getElementById('options').innerHTML='';
  document.getElementById('nextBtn').textContent='Play Again';
  document.getElementById('nextBtn').disabled=false;
  document.getElementById('nextBtn').onclick=()=>{document.getElementById('nextBtn').textContent='Next';document.getElementById('nextBtn').onclick=nextQuestion;initQuiz();};
}
initQuiz();
</script>
</body>
</html>"""


_GAME_TEMPLATES: dict[str, str] = {
    "puzzle": _SLIDING_PUZZLE_HTML,
    "snake": _SNAKE_HTML,
    "breakout": _BREAKOUT_HTML,
    "tetris": _TETRIS_HTML,
    "trivia": _TRIVIA_HTML,
}

# ---------------------------------------------------------------------------
# Animation / chart templates
# ---------------------------------------------------------------------------

_PARTICLES_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Particles</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#0a0a1a}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H,P=[],MOUSE={x:-999,y:-999};
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const COUNT=CFG.count||150,SPEED=CFG.speed||1.5,SIZE=CFG.size||3;
for(let i=0;i<COUNT;i++)P.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-0.5)*SPEED,vy:(Math.random()-0.5)*SPEED,h:Math.random()*360,l:Math.random()*0.5+0.5});
function anim(){
  X.fillStyle='rgba(10,10,26,0.08)';X.fillRect(0,0,W,H);
  for(let p of P){
    let dx=MOUSE.x-p.x,dy=MOUSE.y-p.y,dist=Math.sqrt(dx*dx+dy*dy);
    if(dist<200){p.vx-=dx/dist*0.2;p.vy-=dy/dist*0.2;}
    p.vx*=0.99;p.vy*=0.99;
    if(Math.abs(p.vx)>SPEED*2)p.vx=Math.sign(p.vx)*SPEED*2;
    if(Math.abs(p.vy)>SPEED*2)p.vy=Math.sign(p.vy)*SPEED*2;
    p.x+=p.vx;p.y+=p.vy;
    if(p.x<0)p.x=W;if(p.x>W)p.x=0;if(p.y<0)p.y=H;if(p.y>H)p.y=0;
    X.fillStyle='hsla('+p.h+',80%,60%,'+p.l+')';
    X.beginPath();X.arc(p.x,p.y,SIZE,0,Math.PI*2);X.fill();
  }
  for(let i=0;i<P.length;i++)for(let j=i+1;j<P.length;j++){
    let dx=P[i].x-P[j].x,dy=P[i].y-P[j].y,dist=Math.sqrt(dx*dx+dy*dy);
    if(dist<120){X.strokeStyle='rgba(100,200,255,'+(1-dist/120)*0.15+')';X.lineWidth=1;X.beginPath();X.moveTo(P[i].x,P[i].y);X.lineTo(P[j].x,P[j].y);X.stroke();}
  }
  requestAnimationFrame(anim);
}
C.onmousemove=e=>{MOUSE.x=e.clientX;MOUSE.y=e.clientY;};
C.onmouseleave=()=>{MOUSE.x=-999;MOUSE.y=-999;};
anim();
</script>
</body>
</html>"""


_FIREWORKS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Fireworks</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#0a0a1a;cursor:crosshair}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H;
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const GRAVITY=CFG.gravity||0.05,SPEED=CFG.speed||6;
let ROCKETS=[],PARTICLES=[];
function rand(min,max){return Math.random()*(max-min)+min;}
function createBurst(x,y){
  let count=Math.floor(rand(50,120)),hue=Math.random()*360;
  for(let i=0;i<count;i++){
    let angle=rand(0,Math.PI*2),speed=rand(1,SPEED);
    PARTICLES.push({x,y,vx:Math.cos(angle)*speed,vy:Math.sin(angle)*speed,life:1,decay:rand(0.01,0.03),hue:hue+rand(-20,20),size:rand(2,4)});
  }
}
C.onclick=e=>{
  let x=e.clientX,y=e.clientY;
  ROCKETS.push({x,y,yv:-rand(8,14),trail:[]});
};
function anim(){
  X.fillStyle='rgba(10,10,26,0.15)';X.fillRect(0,0,W,H);
  for(let i=ROCKETS.length-1;i>=0;i--){
    let r=ROCKETS[i];r.y+=r.yv;r.yv+=GRAVITY*1.5;
    if(r.yv>-1){createBurst(r.x+rand(-5,5),r.y+rand(-5,5));ROCKETS.splice(i,1);}
    else{X.fillStyle='#fff';X.beginPath();X.arc(r.x,r.y,2,0,Math.PI*2);X.fill();}
  }
  for(let i=PARTICLES.length-1;i>=0;i--){
    let p=PARTICLES[i];p.x+=p.vx;p.y+=p.vy;p.vy+=GRAVITY;p.vx*=0.98;p.vy*=0.98;p.life-=p.decay;
    if(p.life<=0){PARTICLES.splice(i,1);continue;}
    X.globalAlpha=p.life;X.fillStyle='hsl('+p.hue+',100%,60%)';X.beginPath();X.arc(p.x,p.y,p.size,0,Math.PI*2);X.fill();
  }
  X.globalAlpha=1;
  requestAnimationFrame(anim);
}
anim();
</script>
</body>
</html>"""


_STARS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Stars</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#050510}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H,STARS=[],SHOOTING=[];
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const COUNT=CFG.count||300;
for(let i=0;i<COUNT;i++)STARS.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*2+0.5,b:Math.random(),sp:Math.random()*0.02+0.005,phase:Math.random()*Math.PI*2});
setInterval(()=>{SHOOTING.push({x:Math.random()*W,y:0,vx:(Math.random()-0.5)*4,vy:Math.random()*6+4,life:1,len:Math.random()*60+30});},3000);
function anim(){
  X.fillStyle='rgba(5,5,16,0.3)';X.fillRect(0,0,W,H);
  for(let s of STARS){
    let br=0.5+0.5*Math.sin(s.phase+s.b);
    X.fillStyle='rgba(255,255,255,'+br+')';X.beginPath();X.arc(s.x,s.y,s.r,0,Math.PI*2);X.fill();
  }
  for(let i=SHOOTING.length-1;i>=0;i--){
    let s=SHOOTING[i];s.x+=s.vx;s.y+=s.vy;s.life-=0.01;
    if(s.life<=0){SHOOTING.splice(i,1);continue;}
    X.strokeStyle='rgba(200,220,255,'+s.life+')';X.lineWidth=2;X.beginPath();X.moveTo(s.x,s.y);X.lineTo(s.x-s.vx*2,s.y-s.vy*2);X.stroke();
  }
  requestAnimationFrame(anim);
}
anim();
</script>
</body>
</html>"""


_WAVES_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Waves</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#0a1628}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H,t=0;
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const WAVES=CFG.waves||[{amp:40,freq:0.02,speed:0.01,color:'rgba(233,69,96,0.5)'},{amp:60,freq:0.015,speed:0.015,color:'rgba(78,204,163,0.4)'},{amp:30,freq:0.025,speed:0.008,color:'rgba(15,52,96,0.6)'},{amp:50,freq:0.018,speed:0.012,color:'rgba(100,200,255,0.3)'}];
function anim(){
  X.fillStyle='#0a1628';X.fillRect(0,0,W,H);t++;
  for(let w of WAVES){
    X.beginPath();X.moveTo(0,H/2);
    for(let x=0;x<=W;x+=2){
      let y=H/2+Math.sin(x*w.freq+t*w.speed)*w.amp+Math.sin(x*w.freq*2+t*w.speed*1.5)*w.amp*0.3;
      X.lineTo(x,y);
    }
    X.lineTo(W,H);X.lineTo(0,H);X.closePath();X.fillStyle=w.color;X.fill();
  }
  requestAnimationFrame(anim);
}
anim();
</script>
</body>
</html>"""


_CLOCK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Analog Clock</title>
<style>
*{margin:0;padding:0}
body{background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh}
canvas{background:#16213e;border-radius:50%}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
const S=Math.min(innerWidth,innerHeight)*0.8;const R=S/2-20;
C.width=C.height=S;
const CFG=__CONFIG__;
const SIZE=CFG.size||S;
function draw(){
  X.fillStyle='#16213e';X.fillRect(0,0,S,S);
  X.save();X.translate(S/2,S/2);
  X.beginPath();X.arc(0,0,R,0,Math.PI*2);X.strokeStyle='#0f3460';X.lineWidth=4;X.stroke();
  X.fillStyle='#0f3460';X.beginPath();X.arc(0,0,6,0,Math.PI*2);X.fill();
  for(let i=0;i<12;i++){
    let a=i*Math.PI/6;a-=Math.PI/2;
    X.fillStyle=i%3===0?'#e94560':'#4ecca3';let len=i%3===0?15:8,w=i%3===0?3:1;
    X.fillRect(Math.cos(a)*(R-25)-w/2,Math.sin(a)*(R-25)-w/2,w,len);
  }
  let now=new Date();let h=now.getHours()%12,m=now.getMinutes(),s=now.getSeconds()+now.getMilliseconds()/1000;
  X.strokeStyle='#e94560';X.lineWidth=5;X.beginPath();X.moveTo(0,0);let ha=(h+m/60)*Math.PI/6-Math.PI/2;X.lineTo(Math.cos(ha)*R*0.5,Math.sin(ha)*R*0.5);X.stroke();
  X.strokeStyle='#4ecca3';X.lineWidth=3;X.beginPath();X.moveTo(0,0);let ma=(m+s/60)*Math.PI/30-Math.PI/2;X.lineTo(Math.cos(ma)*R*0.7,Math.sin(ma)*R*0.7);X.stroke();
  X.strokeStyle='#fff';X.lineWidth=1.5;X.beginPath();X.moveTo(0,0);let sa=s*Math.PI/30-Math.PI/2;X.lineTo(Math.cos(sa)*R*0.85,Math.sin(sa)*R*0.85);X.stroke();
  X.restore();requestAnimationFrame(draw);
}
draw();
</script>
</body>
</html>"""


_FRACTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mandelbrot Set</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#000}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H,zoom=1,offsetX=-0.5,offsetY=0;
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;render();}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const MAX=CFG.iterations||100;
function render(){
  let img=X.createImageData(W,H);
  for(let x=0;x<W;x++)for(let y=0;y<H;y++){
    let zx=(x-W/2)/(H*0.4*zoom)+offsetX,zy=(y-H/2)/(H*0.4*zoom)+offsetY;
    let cx=zx,cy=zy,i=0;
    while(i<MAX&&zx*zx+zy*zy<4){let t=zx*zx-zy*zy+cx;zy=2*zx*zy+cy;zx=t;i++;}
    let p=(x+y*W)*4;
    if(i===MAX){img.data[p]=0;img.data[p+1]=0;img.data[p+2]=0;}
    else{let c=i+(1-Math.log(Math.log(Math.sqrt(zx*zx+zy*zy)))/Math.log(2));let hue=Math.floor(c*10+200)%360;let h=c/MAX;img.data[p]=Math.floor(9*(1-h)*h*h*h*255);img.data[p+1]=Math.floor(15*(1-h)*(1-h)*h*h*255);img.data[p+2]=Math.floor(8.5*(1-h)*(1-h)*(1-h)*h*255);}
    img.data[p+3]=255;
  }
  X.putImageData(img,0,0);
}
C.onwheel=e=>{
  e.preventDefault();let z=zoom;zoom*=e.deltaY>0?0.8:1.25;
  let mx=(e.clientX-W/2)/(H*0.4*z)+offsetX,my=(e.clientY-H/2)/(H*0.4*z)+offsetY;
  offsetX=mx-(e.clientX-W/2)/(H*0.4*zoom);offsetY=my-(e.clientY-H/2)/(H*0.4*zoom);render();
};
C.onmousemove=e=>{if(e.buttons&1){offsetX-=(e.movementX)/(H*0.4*zoom);offsetY-=(e.movementY)/(H*0.4*zoom);render();}};
resize();
</script>
</body>
</html>"""


_BOIDS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Boids</title>
<style>
*{margin:0;padding:0}
canvas{display:block;background:#0a0a1a;cursor:crosshair}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const C=document.getElementById('c'),X=C.getContext('2d');
let W,H;
function resize(){W=C.width=innerWidth;H=C.height=innerHeight;}
window.onresize=resize;resize();
const CFG=__CONFIG__;
const COUNT=CFG.count||80,MAX_SPEED=CFG.speed||4,PERCEPTION=CFG.perception||60;
let BOIDS=[],MOUSE={x:-999,y:-999};
for(let i=0;i<COUNT;i++)BOIDS.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-0.5)*2,vy:(Math.random()-0.5)*2});
function sep(b){
  let sx=0,sy=0,c=0;
  for(let o of BOIDS){let d=Math.sqrt((b.x-o.x)**2+(b.y-o.y)**2);if(o!==b&&d<PERCEPTION*0.4){sx+=b.x-o.x;sy+=b.y-o.y;c++;}}
  return c?{x:sx/c,y:sy/c}:{x:0,y:0};
}
function align(b){
  let ax=0,ay=0,c=0;
  for(let o of BOIDS){let d=Math.sqrt((b.x-o.x)**2+(b.y-o.y)**2);if(o!==b&&d<PERCEPTION){ax+=o.vx;ay+=o.vy;c++;}}
  return c?{x:ax/c,y:ay/c}:{x:0,y:0};
}
function coh(b){
  let cx=0,cy=0,c=0;
  for(let o of BOIDS){let d=Math.sqrt((b.x-o.x)**2+(b.y-o.y)**2);if(o!==b&&d<PERCEPTION){cx+=o.x;cy+=o.y;c++;}}
  if(!c)return{x:0,y:0};
  return{x:(cx/c-b.x)*0.01,y:(cy/c-b.y)*0.01};
}
function anim(){
  X.fillStyle='rgba(10,10,26,0.1)';X.fillRect(0,0,W,H);
  for(let b of BOIDS){
    let s=sep(b),a=align(b),c=coh(b);
    let dx=MOUSE.x-b.x,dy=MOUSE.y-b.y,dist=Math.sqrt(dx*dx+dy*dy);
    let mx=0,my=0;
    if(dist<150){mx=-dx/dist*2;my=-dy/dist*2;}
    b.vx+=s.x*0.1+a.x*0.05+c.x+mx;b.vy+=s.y*0.1+a.y*0.05+c.y+my;
    let sp=Math.sqrt(b.vx*b.vx+b.vy*b.vy);
    if(sp>MAX_SPEED){b.vx=(b.vx/sp)*MAX_SPEED;b.vy=(b.vy/sp)*MAX_SPEED;}
    b.x+=b.vx;b.y+=b.vy;
    if(b.x<0)b.x=W;if(b.x>W)b.x=0;if(b.y<0)b.y=H;if(b.y>H)b.y=0;
    let angle=Math.atan2(b.vy,b.vx);
    X.save();X.translate(b.x,b.y);X.rotate(angle);
    X.fillStyle='rgba(78,204,163,0.8)';X.beginPath();X.moveTo(6,0);X.lineTo(-4,-3);X.lineTo(-4,3);X.closePath();X.fill();
    X.restore();
  }
  requestAnimationFrame(anim);
}
C.onmousemove=e=>{MOUSE.x=e.clientX;MOUSE.y=e.clientY;};
C.onmouseleave=()=>{MOUSE.x=-999;MOUSE.y=-999;};
anim();
</script>
</body>
</html>"""

# Chart templates (configurable via __CONFIG__)

_BAR_CHART_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bar Chart</title>
<style>
*{margin:0;padding:0}
body{background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif}
canvas{background:#16213e;border-radius:8px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const CFG=__CONFIG__;
const DATA=CFG.data||[10,20,30,40,50];const LABELS=CFG.labels||DATA.map((_,i)=>'Item '+(i+1));const COLORS=CFG.colors||['#e94560','#4ecca3','#f5a623','#0f3460','#a000f0','#00f0f0','#f0f000','#f00000'];const TITLE=CFG.title||'Bar Chart';
const C=document.getElementById('c'),X=C.getContext('2d');
const W=700,H=500,PAD={top:60,bottom:60,left:70,right:40};
C.width=W;C.height=H;
let max=Math.max(...DATA,1),gap=10,bw=(W-PAD.left-PAD.right-gap*(DATA.length-1))/DATA.length;
X.fillStyle='#16213e';X.fillRect(0,0,W,H);
X.fillStyle='#fff';X.font='bold 22px Arial';X.textAlign='center';X.fillText(TITLE,W/2,35);
X.strokeStyle='#0f3460';X.lineWidth=1;
X.beginPath();X.moveTo(PAD.left,PAD.top);X.lineTo(PAD.left,H-PAD.bottom);X.lineTo(W-PAD.right,H-PAD.bottom);X.stroke();
for(let i=0;i<=4;i++){let v=(max/4)*i,y=H-PAD.bottom-(H-PAD.top-PAD.bottom)*i/max;X.fillStyle='#888';X.font='12px Arial';X.textAlign='right';X.fillText(Math.round(v),PAD.left-8,y+4);X.strokeStyle='rgba(255,255,255,0.05)';X.beginPath();X.moveTo(PAD.left,y);X.lineTo(W-PAD.right,y);X.stroke();}
for(let i=0;i<DATA.length;i++){
  let bh=(DATA[i]/max)*(H-PAD.top-PAD.bottom),x=PAD.left+i*(bw+gap),y=H-PAD.bottom-bh;
  let g=X.createLinearGradient(x,y,x,H-PAD.bottom);
  g.addColorStop(0,COLORS[i%COLORS.length]);g.addColorStop(1,COLORS[(i+1)%COLORS.length]);
  X.fillStyle=g;X.beginPath();X.roundRect(x,y,bw,bh,[4,4,0,0]);X.fill();
  X.fillStyle='#aaa';X.font='12px Arial';X.textAlign='center';X.fillText(LABELS[i],x+bw/2,H-PAD.bottom+18);
  X.fillStyle='#fff';X.font='bold 13px Arial';X.fillText(DATA[i],x+bw/2,y-8);
}
</script>
</body>
</html>"""


_LINE_CHART_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Line Chart</title>
<style>
*{margin:0;padding:0}
body{background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif}
canvas{background:#16213e;border-radius:8px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const CFG=__CONFIG__;
const DATA=CFG.data||[10,25,15,40,30,50,35];const LABELS=CFG.labels||DATA.map((_,i)=>'P'+(i+1));const COLORS=CFG.colors||['#4ecca3','#e94560'];const TITLE=CFG.title||'Line Chart';const DATA2=CFG.data2||null;
const C=document.getElementById('c'),X=C.getContext('2d');
const W=700,H=500,PAD={top:60,bottom:60,left:60,right:40};
C.width=W;C.height=H;
let max=Math.max(...DATA,DATA2?Math.max(...DATA2):0,1);
function drawLine(data,color,fill){
  let pts=data.map((v,i)=>({x:PAD.left+i*(W-PAD.left-PAD.right)/(data.length-1),y:H-PAD.bottom-(v/max)*(H-PAD.top-PAD.bottom)}));
  X.beginPath();X.moveTo(pts[0].x,pts[0].y);
  for(let i=1;i<pts.length;i++){let xc=(pts[i].x+pts[i-1].x)/2,yc=(pts[i].y+pts[i-1].y)/2;X.quadraticCurveTo(pts[i-1].x,pts[i-1].y,xc,yc);}
  X.lineTo(pts[pts.length-1].x,pts[pts.length-1].y);
  if(fill){X.lineTo(pts[pts.length-1].x,H-PAD.bottom);X.lineTo(pts[0].x,H-PAD.bottom);X.closePath();X.fillStyle=color.replace(')',',0.15)').replace('rgb','rgba');X.fill();}
  X.strokeStyle=color;X.lineWidth=3;X.stroke();
  for(let p of pts){X.fillStyle=color;X.beginPath();X.arc(p.x,p.y,5,0,Math.PI*2);X.fill();X.fillStyle='#fff';X.beginPath();X.arc(p.x,p.y,2.5,0,Math.PI*2);X.fill();}
}
X.fillStyle='#16213e';X.fillRect(0,0,W,H);
X.fillStyle='#fff';X.font='bold 22px Arial';X.textAlign='center';X.fillText(TITLE,W/2,35);
X.strokeStyle='#0f3460';X.lineWidth=1;
X.beginPath();X.moveTo(PAD.left,PAD.top);X.lineTo(PAD.left,H-PAD.bottom);X.lineTo(W-PAD.right,H-PAD.bottom);X.stroke();
for(let i=0;i<=4;i++){let v=(max/4)*i,y=H-PAD.bottom-(H-PAD.top-PAD.bottom)*i/max;X.fillStyle='#888';X.font='12px Arial';X.textAlign='right';X.fillText(Math.round(v),PAD.left-8,y+4);X.strokeStyle='rgba(255,255,255,0.05)';X.beginPath();X.moveTo(PAD.left,y);X.lineTo(W-PAD.right,y);X.stroke();}
for(let i=0;i<DATA.length;i++){X.fillStyle='#aaa';X.font='11px Arial';X.textAlign='center';let x=PAD.left+i*(W-PAD.left-PAD.right)/(DATA.length-1);X.fillText(LABELS[i],x,H-PAD.bottom+18);}
drawLine(DATA,COLORS[0],true);
if(DATA2)drawLine(DATA2,COLORS[1]||'#e94560',false);
</script>
</body>
</html>"""


_PIE_CHART_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pie Chart</title>
<style>
*{margin:0;padding:0}
body{background:#1a1a2e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif}
canvas{background:#16213e;border-radius:8px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const CFG=__CONFIG__;
const DATA=CFG.data||[30,25,20,15,10];const LABELS=CFG.labels||['A','B','C','D','E'];const COLORS=CFG.colors||['#e94560','#4ecca3','#f5a623','#0f3460','#a000f0','#00f0f0','#f0f000','#f00000'];const TITLE=CFG.title||'Pie Chart';const DONUT=CFG.donut||false;
const C=document.getElementById('c'),X=C.getContext('2d');
const W=700,H=500,CX=300,CY=H/2,R=Math.min(CX-60,CY-60);
C.width=W;C.height=H;
let total=DATA.reduce((a,b)=>a+b,0),start=0,i=0;
X.fillStyle='#16213e';X.fillRect(0,0,W,H);
X.fillStyle='#fff';X.font='bold 22px Arial';X.textAlign='center';X.fillText(TITLE,W/2,35);
for(let v of DATA){
  let angle=(v/total)*Math.PI*2;
  X.fillStyle=COLORS[i%COLORS.length];X.beginPath();X.moveTo(CX,CY);X.arc(CX,CY,R,start,start+angle);X.closePath();X.fill();
  if(DONUT){X.fillStyle='#16213e';X.beginPath();X.arc(CX,CY,R*0.5,0,Math.PI*2);X.fill();}
  let mid=start+angle/2,lx=CX+Math.cos(mid)*(R+20),ly=CY+Math.sin(mid)*(R+20);
  X.fillStyle='#fff';X.font='13px Arial';X.textAlign='center';X.fillText(LABELS[i]+' ('+Math.round(v/total*100)+'%)',lx,ly);
  start+=angle;i++;
}
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Document CSS
# ---------------------------------------------------------------------------

_DOCUMENT_CSS = """
body{font-family:Georgia,'Times New Roman',serif;max-width:800px;margin:0 auto;padding:40px 20px;line-height:1.6;color:#333;background:#fff}
h1,h2,h3,h4{color:#1a1a2e;margin-top:24px;margin-bottom:16px;font-weight:600;line-height:1.25}
h1{font-size:2em;border-bottom:2px solid #e94560;padding-bottom:8px}
h2{font-size:1.5em;border-bottom:1px solid #eaecef;padding-bottom:6px}
h3{font-size:1.25em}
p{margin-bottom:16px}
a{color:#e94560;text-decoration:none}
a:hover{text-decoration:underline}
code{background:#f6f8fa;padding:2px 6px;border-radius:3px;font-size:0.9em;font-family:'SFMono-Regular',Consolas,monospace}
pre{background:#f6f8fa;padding:16px;border-radius:6px;overflow-x:auto;margin-bottom:16px;border:1px solid #eaecef}
pre code{background:none;padding:0;border-radius:0}
blockquote{border-left:4px solid #e94560;padding-left:16px;color:#666;margin:0 0 16px 0}
ul,ol{padding-left:2em;margin-bottom:16px}
li{margin-bottom:4px}
table{border-collapse:collapse;width:100%;margin-bottom:16px}
th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}
th{background:#f6f8fa;font-weight:600}
img{max-width:100%;height:auto;border-radius:4px}
hr{border:none;border-top:1px solid #eaecef;margin:24px 0}
"""

# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


async def artifact_create_website(
    html_content: str = "",
    title: str = "Untitled",
    css_content: str = "",
    js_content: str = "",
) -> dict:
    """Create a website artifact from HTML/CSS/JS content.

    Parameters
    ----------
    html_content : body HTML content placed inside #app
    title : page title and artifact label
    css_content : CSS styles (without <style> tags)
    js_content : JavaScript (without <script> tags)
    """
    body = f'<div id="app">{html_content}</div>' if html_content else ""
    full = _wrap_html(title, body, css_content, js_content)
    return _save_artifact(full, title, "website")


async def artifact_create_game(description: str = "", genre: str = "puzzle") -> dict:
    """Generate a complete playable HTML5 game.

    Parameters
    ----------
    description : description of the desired game (used as title when non-empty)
    genre : puzzle, snake, breakout, tetris, trivia
    """
    genre = genre.lower()
    if genre not in _GAME_TEMPLATES:
        return {
            "success": False,
            "error": f"Unsupported genre: {genre}. Supported: {', '.join(_GAME_TEMPLATES)}",
        }
    title = description or f"{genre.title()} Game"
    html = _GAME_TEMPLATES[genre]
    return _save_artifact(html, title, "game", {"genre": genre})


async def artifact_create_svg(svg_content: str = "", title: str = "SVG Graphic") -> dict:
    """Create an SVG graphic wrapped in an HTML page for browser preview.

    Parameters
    ----------
    svg_content : raw SVG markup (with or without <svg> tags)
    title : artifact title
    """
    if not svg_content.startswith("<svg"):
        svg_content = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>{svg_content}</svg>"
    body = f'<div style="display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f5f5f5">{svg_content}</div>'
    full = _wrap_html(title, body)
    return _save_artifact(full, title, "svg")


async def artifact_create_animation(animation_type: str = "particles", config_json: str = "{}") -> dict:
    """Create an HTML5 Canvas animation or chart.

    Parameters
    ----------
    animation_type : particles, fireworks, stars, waves, clock, fractal, boids,
                     bar_chart, line_chart, pie_chart
    config_json : JSON string with configuration options
                  (data, labels, colors, title for charts; count, speed, etc. for others)
    """
    animation_type = animation_type.lower()

    _ANIMATION_MAP: dict[str, str] = {
        "particles": _PARTICLES_HTML,
        "fireworks": _FIREWORKS_HTML,
        "stars": _STARS_HTML,
        "waves": _WAVES_HTML,
        "clock": _CLOCK_HTML,
        "fractal": _FRACTAL_HTML,
        "boids": _BOIDS_HTML,
        "bar_chart": _BAR_CHART_HTML,
        "line_chart": _LINE_CHART_HTML,
        "pie_chart": _PIE_CHART_HTML,
    }

    if animation_type not in _ANIMATION_MAP:
        return {
            "success": False,
            "error": f"Unsupported animation type: {animation_type}. Supported: {', '.join(_ANIMATION_MAP)}",
        }

    try:
        config = json.loads(config_json) if config_json else {}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid config_json: {e}"}

    html = _ANIMATION_MAP[animation_type].replace("__CONFIG__", json.dumps(config))
    title = config.get("title", animation_type.replace("_", " ").title())
    return _save_artifact(html, title, "animation", {"animation_type": animation_type})


async def artifact_create_document(content: str = "", format: str = "markdown", title: str = "Document") -> dict:
    """Create a formatted document artifact.

    Parameters
    ----------
    content : document content
    format : markdown (rendered to styled HTML), html, plain
    title : artifact title
    """
    fmt = format.lower()

    if fmt == "markdown":
        html_body = _render_markdown(content)
    elif fmt == "html":
        html_body = content
    elif fmt == "plain":
        html_body = f"<pre>{content}</pre>"
    else:
        return {
            "success": False,
            "error": f"Unsupported format: {format}. Supported: markdown, html, plain",
        }

    full = _wrap_html(title, html_body, css=_DOCUMENT_CSS)
    return _save_artifact(full, title, "document", {"format": fmt})


async def artifact_list(limit: int = 20) -> dict:
    """List all created artifacts.

    Parameters
    ----------
    limit : maximum number of artifacts to return (default 20)
    """
    if not os.path.isdir(ARTIFACT_DIR):
        return {"success": True, "artifacts": [], "count": 0}

    entries: list[dict] = []
    for name in os.listdir(ARTIFACT_DIR):
        folder = os.path.join(ARTIFACT_DIR, name)
        index = os.path.join(folder, "index.html")
        if not os.path.isfile(index):
            continue
        try:
            mtime = os.path.getmtime(index)
            size = os.path.getsize(index)
        except OSError:
            continue

        # Try to extract metadata from name
        parts = name.split("-")
        artifact_id = parts[-1] if len(parts) > 1 and len(parts[-1]) == 8 else name[:8]
        title = "-".join(parts[:-1]) if len(parts) > 1 else name

        entries.append({
            "artifact_id": artifact_id,
            "title": title,
            "file_path": index,
            "file_size": size,
            "created_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
        })

    entries.sort(key=lambda e: e["created_at"], reverse=True)
    if limit:
        entries = entries[:limit]

    return {"success": True, "artifacts": entries, "count": len(entries)}


async def artifact_open(artifact_id: str) -> dict:
    """Open a specific artifact in the browser.

    Parameters
    ----------
    artifact_id : the 8-character artifact ID returned by creation functions
    """
    if not os.path.isdir(ARTIFACT_DIR):
        return {"success": False, "error": "No artifacts directory found"}

    for name in os.listdir(ARTIFACT_DIR):
        if name.endswith(f"-{artifact_id}") or name.startswith(artifact_id):
            index = os.path.join(ARTIFACT_DIR, name, "index.html")
            if os.path.isfile(index):
                webbrowser.open(f"file://{os.path.abspath(index)}")
                return {"success": True, "file_path": index, "artifact_id": artifact_id}

    return {"success": False, "error": f"Artifact '{artifact_id}' not found"}


async def artifact_delete(artifact_id: str) -> dict:
    """Delete an artifact by ID.

    Parameters
    ----------
    artifact_id : the 8-character artifact ID returned by creation functions
    """
    if not os.path.isdir(ARTIFACT_DIR):
        return {"success": False, "error": "No artifacts directory found"}

    for name in os.listdir(ARTIFACT_DIR):
        if name.endswith(f"-{artifact_id}") or name.startswith(artifact_id):
            folder = os.path.join(ARTIFACT_DIR, name)
            try:
                import shutil
                shutil.rmtree(folder)
                return {"success": True, "artifact_id": artifact_id}
            except OSError as e:
                return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Artifact '{artifact_id}' not found"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _render_markdown(text: str) -> str:
    """Convert Markdown text to HTML, trying markdown library first."""
    try:
        import markdown as _md
        return _md.markdown(text, extensions=["extra", "codehilite", "tables"])
    except ImportError:
        pass

    lines = text.split("\n")
    html_parts: list[str] = []
    i = 0
    n = len(lines)

    def _inline(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
        return s

    def _is_code_fence(line: str) -> bool:
        return line.startswith("```")

    in_code = False
    code_buf: list[str] = []
    in_list = False
    list_type = "ul"
    list_buf: list[str] = []
    in_blockquote = False
    quote_buf: list[str] = []

    def _flush_list():
        nonlocal list_buf, in_list
        if list_buf:
            tag = "ol" if list_type == "ol" else "ul"
            html_parts.append(f"<{tag}>")
            for item in list_buf:
                html_parts.append(f"<li>{_inline(item)}</li>")
            html_parts.append(f"</{tag}>")
            list_buf = []
            in_list = False

    def _flush_quote():
        nonlocal quote_buf, in_blockquote
        if quote_buf:
            html_parts.append("<blockquote>")
            for ql in quote_buf:
                html_parts.append(f"<p>{_inline(ql)}</p>")
            html_parts.append("</blockquote>")
            quote_buf = []
            in_blockquote = False

    while i < n:
        line = lines[i]

        if _is_code_fence(line):
            _flush_list()
            _flush_quote()
            if in_code:
                lang = line[3:].strip()
                html_parts.append(
                    f"<pre><code class='language-{lang}'>{'\n'.join(code_buf)}</code></pre>"
                )
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Headings
        hm = re.match(r"^(#{1,6})\s+(.+)$", line)
        if hm:
            _flush_list()
            _flush_quote()
            level = len(hm.group(1))
            html_parts.append(f"<h{level}>{_inline(hm.group(2))}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line) or re.match(r"^\*\*\*+\s*$", line):
            _flush_list()
            _flush_quote()
            html_parts.append("<hr>")
            i += 1
            continue

        # Blockquote
        bqm = re.match(r"^>\s*(.*)$", line)
        if bqm:
            _flush_list()
            if not in_blockquote:
                _flush_quote()
                in_blockquote = True
            quote_buf.append(bqm.group(1) or "&nbsp;")
            i += 1
            continue
        else:
            _flush_quote()

        # Unordered list
        ulm = re.match(r"^[*-]\s+(.+)$", line)
        if ulm:
            if not in_list or list_type != "ul":
                _flush_list()
                in_list = True
                list_type = "ul"
            list_buf.append(ulm.group(1))
            i += 1
            continue

        # Ordered list
        olm = re.match(r"^\d+\.\s+(.+)$", line)
        if olm:
            if not in_list or list_type != "ol":
                _flush_list()
                in_list = True
                list_type = "ol"
            list_buf.append(olm.group(1))
            i += 1
            continue

        _flush_list()

        # Empty line = paragraph break
        if not line.strip():
            i += 1
            continue

        # Table
        if "|" in line and i + 1 < n and re.match(r"^[\s|:-]+$", lines[i + 1]):
            rows: list[list[str]] = []
            while i < n and "|" in lines[i]:
                cells = [c.strip() for c in lines[i].split("|") if c.strip()]
                if cells:
                    rows.append(cells)
                i += 1
            if rows:
                html_parts.append("<table>")
                for ri, row in enumerate(rows):
                    tag = "th" if ri == 0 else "td"
                    html_parts.append("<tr>")
                    for cell in row:
                        html_parts.append(f"<{tag}>{_inline(cell)}</{tag}>")
                    html_parts.append("</tr>")
                html_parts.append("</table>")
            continue

        # Paragraph
        para: list[str] = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_code_fence(lines[i]) and not re.match(r"^[#>*-]|\d+\.\s", lines[i]) and "|" not in lines[i]:
            para.append(lines[i])
            i += 1
        html_parts.append(f"<p>{_inline(' '.join(para))}</p>")

    _flush_list()
    _flush_quote()
    if in_code and code_buf:
        html_parts.append(f"<pre><code>{'\n'.join(code_buf)}</code></pre>")

    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Spec-based website generation
# ---------------------------------------------------------------------------

def _gen_section_hero(s: dict) -> tuple[str, str]:
    t = s.get("title", "")
    st = s.get("subtitle", "")
    cta = s.get("cta", "")
    html = f"""<section class="hero">
  <div class="hero-content">
    <h1>{t}</h1>
    <p class="subtitle">{st}</p>
    <a class="btn-primary" href="#">{cta}</a>
  </div>
</section>"""
    css = """.hero{min-height:80vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:40px 20px;background:linear-gradient(135deg,var(--primary),var(--primary-dark))}.hero-content{max-width:700px}.hero h1{font-size:clamp(2rem,5vw,3.5rem);margin-bottom:16px;color:#fff}.hero .subtitle{font-size:clamp(1rem,2vw,1.25rem);color:rgba(255,255,255,0.85);margin-bottom:32px}.btn-primary{display:inline-block;padding:14px 36px;background:#fff;color:var(--primary);border-radius:50px;font-weight:600;font-size:1.1rem;text-decoration:none;transition:transform .2s,box-shadow .2s;box-shadow:0 4px 15px rgba(0,0,0,0.2)}.btn-primary:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,0.3)}"""
    return html, css


def _gen_section_features(s: dict) -> tuple[str, str]:
    items = s.get("items", [])
    cards = "".join(
        f"""<div class="feat-card"><div class="feat-icon">{i.get("icon","★")}</div><h3>{i.get("title","")}</h3><p>{i.get("desc","")}</p></div>"""
        for i in items
    )
    html = f"""<section class="features"><div class="container"><h2 class="section-title">{s.get("title","Features")}</h2><div class="feat-grid">{cards}</div></div></section>"""
    css = """.features{padding:80px 20px;background:var(--bg)}.container{max-width:1100px;margin:0 auto}.section-title{text-align:center;font-size:2rem;margin-bottom:48px;color:var(--text)}.feat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:30px}.feat-card{background:var(--card-bg);padding:32px 24px;border-radius:12px;text-align:center;transition:transform .2s,box-shadow .2s;border:1px solid var(--border)}.feat-card:hover{transform:translateY(-4px);box-shadow:0 8px 25px rgba(0,0,0,0.1)}.feat-icon{font-size:2.5rem;margin-bottom:16px}.feat-card h3{margin-bottom:12px;color:var(--text)}.feat-card p{color:var(--text-muted);line-height:1.6;font-size:0.95rem}"""
    return html, css


def _gen_section_pricing(s: dict) -> tuple[str, str]:
    plans = s.get("plans", [])
    cards = "".join(
        f"""<div class="plan-card"><h3>{p.get("name","")}</h3><div class="price">{p.get("price","$0")}<span>/mo</span></div><ul class="plan-features">{"".join(f"<li>{f}</li>" for f in p.get("features",[]))}</ul><a class="btn-outline" href="#">Choose</a></div>"""
        for p in plans
    )
    html = f"""<section class="pricing"><div class="container"><h2 class="section-title">{s.get("title","Pricing")}</h2><div class="pricing-grid">{cards}</div></div></section>"""
    css = """.pricing{padding:80px 20px;background:var(--bg-alt)}.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:30px;max-width:900px;margin:0 auto}.plan-card{background:var(--card-bg);padding:36px 24px;border-radius:12px;text-align:center;border:1px solid var(--border);transition:transform .2s}.plan-card:hover{transform:translateY(-4px)}.plan-card h3{font-size:1.25rem;margin-bottom:16px;color:var(--text)}.price{font-size:2.5rem;font-weight:700;color:var(--primary);margin-bottom:8px}.price span{font-size:1rem;color:var(--text-muted);font-weight:400}.plan-features{list-style:none;padding:0;margin:24px 0}.plan-features li{padding:8px 0;border-bottom:1px solid var(--border);color:var(--text-muted);font-size:0.95rem}.plan-features li:last-child{border-bottom:none}.btn-outline{display:inline-block;padding:12px 32px;border:2px solid var(--primary);color:var(--primary);border-radius:50px;font-weight:600;text-decoration:none;transition:all .2s}.btn-outline:hover{background:var(--primary);color:#fff}"""
    return html, css


def _gen_section_contact(s: dict) -> tuple[str, str]:
    email = s.get("email", "")
    html = f"""<section class="contact"><div class="container"><h2 class="section-title">{s.get("title","Contact")}</h2><div class="contact-content"><p>Get in touch</p><a class="contact-email" href="mailto:{email}">{email}</a></div></div></section>"""
    css = """.contact{padding:80px 20px;background:var(--bg)}.contact-content{text-align:center;max-width:500px;margin:0 auto}.contact-content p{margin-bottom:16px;color:var(--text-muted);font-size:1.1rem}.contact-email{font-size:1.5rem;color:var(--primary);text-decoration:none;font-weight:600;transition:opacity .2s}.contact-email:hover{opacity:0.8}"""
    return html, css


def _gen_section_header(s: dict) -> tuple[str, str]:
    title = s.get("title", "Site")
    links = "".join(f"<a href='#'>{l}</a>" for l in s.get("links", ["Home", "About", "Contact"]))
    html = f"""<header class="site-header"><div class="header-inner"><div class="logo">{title}</div><nav class="nav">{links}</nav></div></header>"""
    css = """.site-header{position:sticky;top:0;z-index:100;background:var(--header-bg);backdrop-filter:blur(10px);border-bottom:1px solid var(--border)}.header-inner{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;padding:16px 20px}.logo{font-size:1.3rem;font-weight:700;color:var(--text)}.nav{display:flex;gap:24px}.nav a{text-decoration:none;color:var(--text-muted);font-weight:500;transition:color .2s}.nav a:hover{color:var(--primary)}"""
    return html, css


def _gen_section_footer(s: dict) -> tuple[str, str]:
    html = """<footer class="site-footer"><div class="footer-inner"><p>&copy; 2025 All rights reserved.</p></div></footer>"""
    css = """.site-footer{background:var(--bg-alt);border-top:1px solid var(--border);padding:24px 20px;text-align:center}.footer-inner{max-width:1100px;margin:0 auto}.footer-inner p{color:var(--text-muted);font-size:0.9rem}"""
    return html, css


def _gen_section_hero_image(s: dict) -> tuple[str, str]:
    t = s.get("title", "")
    st = s.get("subtitle", "")
    img = s.get("image", "")
    cta = s.get("cta", "Learn More")
    html = f"""<section class="hero-image"><div class="hero-image-content"><h1>{t}</h1><p>{st}</p><a class="btn-primary" href="#">{cta}</a></div><div class="hero-image-visual">{f'<img src="{img}" alt="">' if img else '<div class="placeholder-img"></div>'}</div></section>"""
    css = """.hero-image{display:grid;grid-template-columns:1fr 1fr;align-items:center;min-height:70vh;padding:60px 40px;gap:40px;background:var(--bg)}.hero-image-content h1{font-size:clamp(2rem,4vw,3rem);margin-bottom:16px;color:var(--text)}.hero-image-content p{font-size:1.1rem;color:var(--text-muted);margin-bottom:32px}.hero-image-visual{display:flex;justify-content:center}.placeholder-img{width:100%;max-width:450px;aspect-ratio:4/3;background:linear-gradient(135deg,var(--primary),var(--primary-dark));border-radius:16px;opacity:0.6}.hero-image-visual img{max-width:100%;border-radius:16px}@media(max-width:768px){.hero-image{grid-template-columns:1fr}}"""
    return html, css


def _gen_section_gallery(s: dict) -> tuple[str, str]:
    images = s.get("images", [f"https://picsum.photos/seed/{i}/400/300" for i in range(6)])
    items = "".join(f'<div class="gallery-item"><img src="{img}" alt="Gallery"></div>' for img in images[:12])
    html = f"""<section class="gallery"><div class="container"><h2 class="section-title">{s.get("title","Gallery")}</h2><div class="gallery-grid">{items}</div></div></section>"""
    css = """.gallery{padding:80px 20px;background:var(--bg-alt)}.gallery-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}.gallery-item{overflow:hidden;border-radius:8px;transition:transform .3s}.gallery-item:hover{transform:scale(1.03)}.gallery-item img{width:100%;height:200px;object-fit:cover;display:block;border-radius:8px}"""
    return html, css


def _gen_section_testimonials(s: dict) -> tuple[str, str]:
    items = s.get("items", [{"quote": "Great product!", "author": "User", "role": "Customer"}])
    cards = "".join(
        f"""<div class="testimonial-card"><div class="quote">&#10077;{i.get("quote","")}&#10078;</div><div class="author-name">{i.get("author","")}</div><div class="author-role">{i.get("role","")}</div></div>"""
        for i in items
    )
    html = f"""<section class="testimonials"><div class="container"><h2 class="section-title">{s.get("title","Testimonials")}</h2><div class="testimonial-grid">{cards}</div></div></section>"""
    css = """.testimonials{padding:80px 20px;background:var(--bg)}.testimonial-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:30px;max-width:900px;margin:0 auto}.testimonial-card{background:var(--card-bg);padding:32px 24px;border-radius:12px;border:1px solid var(--border);text-align:center}.quote{font-size:1.15rem;line-height:1.6;color:var(--text);margin-bottom:20px;font-style:italic}.author-name{font-weight:600;color:var(--text)}.author-role{font-size:0.85rem;color:var(--text-muted);margin-top:4px}"""
    return html, css


def _gen_section_stats(s: dict) -> tuple[str, str]:
    items = s.get("items", [{"num": "99%", "label": "Uptime"}, {"num": "10K+", "label": "Users"}])
    cards = "".join(f'<div class="stat-card"><div class="stat-num">{i.get("num","0")}</div><div class="stat-label">{i.get("label","")}</div></div>' for i in items)
    html = f"""<section class="stats"><div class="container"><div class="stats-grid">{cards}</div></div></section>"""
    css = """.stats{padding:60px 20px;background:linear-gradient(135deg,var(--primary),var(--primary-dark))}.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:30px;text-align:center}.stat-num{font-size:2.5rem;font-weight:700;color:#fff}.stat-label{font-size:1rem;color:rgba(255,255,255,0.8);margin-top:4px}"""
    return html, css


def _gen_section_cta(s: dict) -> tuple[str, str]:
    t = s.get("title", "Ready to Start?")
    btn = s.get("button", "Get Started")
    html = f"""<section class="cta-section"><div class="container"><h2>{t}</h2><a class="btn-primary" href="#">{btn}</a></div></section>"""
    css = """.cta-section{padding:80px 20px;background:var(--bg-alt);text-align:center}.cta-section h2{font-size:2rem;margin-bottom:32px;color:var(--text)}"""
    return html, css


_SECTION_GENERATORS = {
    "hero": _gen_section_hero,
    "features": _gen_section_features,
    "pricing": _gen_section_pricing,
    "contact": _gen_section_contact,
    "header": _gen_section_header,
    "footer": _gen_section_footer,
    "hero_image": _gen_section_hero_image,
    "gallery": _gen_section_gallery,
    "testimonials": _gen_section_testimonials,
    "stats": _gen_section_stats,
    "cta": _gen_section_cta,
}


def _build_website(spec: dict) -> str:
    title = spec.get("title", "Website")
    theme = spec.get("theme", {})
    primary = theme.get("primary", "#3498db")
    secondary = theme.get("secondary", "#2ecc71")
    is_dark = theme.get("dark", False)

    if is_dark:
        bg = "#0f0f1a"
        bg_alt = "#1a1a2e"
        text = "#e0e0e0"
        text_muted = "#999"
        card_bg = "#1e1e32"
        border = "rgba(255,255,255,0.08)"
        header_bg = "rgba(15,15,26,0.9)"
    else:
        bg = "#ffffff"
        bg_alt = "#f8f9fa"
        text = "#1a1a2e"
        text_muted = "#666"
        card_bg = "#ffffff"
        border = "rgba(0,0,0,0.08)"
        header_bg = "rgba(255,255,255,0.9)"

    css_vars = f""":root{{--primary:{primary};--primary-dark:{primary}dd;--secondary:{secondary};--bg:{bg};--bg-alt:{bg_alt};--text:{text};--text-muted:{text_muted};--card-bg:{card_bg};--border:{border};--header-bg:{header_bg};--radius:8px}}*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}}a{{color:var(--primary);text-decoration:none}}img{{max-width:100%;height:auto}}"""

    sections_html = []
    sections_css = []
    for s in spec.get("sections", []):
        t = s.get("type", "")
        gen = _SECTION_GENERATORS.get(t)
        if gen:
            h, c = gen(s)
            sections_html.append(h)
            sections_css.append(c)

    body = "\n".join(sections_html)
    css = css_vars + "\n" + "\n".join(sections_css)
    return _wrap_html(title, body, css)


async def artifact_create_website_from_spec(spec_json: str) -> dict:
    """Create a complete website from a JSON specification.

    Parameters
    ----------
    spec_json : JSON string describing the website layout and sections
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid spec_json: {e}"}

    try:
        html = _build_website(spec)
        title = spec.get("title", "Website")
        return _save_artifact(html, title, "website_spec", {"type": "website_spec"})
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Spec-based game generation
# ---------------------------------------------------------------------------

def _build_platformer(spec: dict) -> str:
    colors = spec.get("colors", {})
    bg = colors.get("bg", "#1a1a2e")
    pc = colors.get("player", "#e94560")
    plc = colors.get("platform", "#16213e")
    cc = colors.get("coin", "#ffd700")
    title = spec.get("title", "Platformer")
    theme = spec.get("theme", "dark")
    grav = "true" if spec.get("mechanics", {}).get("gravity", True) else "false"
    jump = "true" if spec.get("mechanics", {}).get("jumping", True) else "false"
    ms = spec.get("mechanics", {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{bg};display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif;color:#fff}}
canvas{{border:2px solid {plc};border-radius:4px;display:block}}
.game-container{{text-align:center}}
h1{{color:{pc};margin-bottom:12px}}
.info{{font-size:16px;margin:8px 0}}
.info span{{color:{cc};font-weight:bold}}
.game-over{{color:{pc};font-size:20px;margin-top:8px;display:none}}
button{{padding:10px 24px;font-size:16px;background:{pc};color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}}
button:hover{{opacity:0.85}}
.hint{{color:#888;font-size:13px;margin-top:6px}}
</style>
</head>
<body>
<div class="game-container">
<h1>{title}</h1>
<div class="info">Score: <span id="score">0</span></div>
<canvas id="game" width="480" height="640"></canvas>
<div class="game-over" id="over">Game Over! Score: <span id="final"></span></div>
<button onclick="init()">New Game</button>
<div class="hint">Arrow keys / WASD to move &middot; Space to jump</div>
</div>
<script>
const C=document.getElementById('game'),X=C.getContext('2d');
const W=480,H=640,G=0.5,J=-10,PS=24;
let player,platforms,coins,score,gameOver,keys={{}},loop;
const COLORS={{bg:'{bg}',player:'{pc}',plat:'{plc}',coin:'{cc}'}};
function init(){{
  score=0;gameOver=false;
  document.getElementById('score').textContent='0';
  document.getElementById('over').style.display='none';
  player={{x:W/2-PS/2,y:H-100,w:PS,h:PS,vy:0,onGround:false}};
  platforms=[];
  for(let i=0;i<8;i++){{
    let pw=80+Math.random()*120,px=Math.random()*(W-pw),py=H-60-i*70-Math.random()*20;
    platforms.push({{x:px,y:py,w:pw,h:14}});
  }}
  coins=[];
  for(let i=0;i<5;i++){{
    let p=platforms[i];
    coins.push({{x:p.x+p.w/2-6,y:p.y-20,w:12,h:12,collected:false}});
  }}
  if(loop)cancelAnimationFrame(loop);
  loop=requestAnimationFrame(tick);
}}
function tick(){{
  if(gameOver){{loop=requestAnimationFrame(tick);return;}}
  update();
  draw();
  if(!gameOver)loop=requestAnimationFrame(tick);
}}
function update(){{
  let dx=0;
  if(keys['ArrowLeft']||keys['KeyA'])dx=-4;
  if(keys['ArrowRight']||keys['KeyD'])dx=4;
  if({jump}&&(keys['Space']||keys['ArrowUp']||keys['KeyW'])&&player.onGround){{player.vy=J;player.onGround=false;}}
  player.vy+=G;
  player.x+=dx;
  player.y+=player.vy;
  if(player.x<0)player.x=0;
  if(player.x+player.w>W)player.x=W-player.w;
  player.onGround=false;
  for(let p of platforms){{
    if(player.vy>=0&&player.y+player.h>p.y&&player.y+player.h<p.y+p.h+8&&player.x+player.w>p.x+4&&player.x<p.x+p.w-4){{
      player.y=p.y-player.h;player.vy=0;player.onGround=true;
    }}
  }}
  if(player.y+player.h>H){{endGame();return;}}
  for(let c of coins){{
    if(!c.collected&&player.x+player.w>c.x&&player.x<c.x+c.w&&player.y+player.h>c.y&&player.y<c.y+c.h){{
      c.collected=true;score+=10;document.getElementById('score').textContent=score;
    }}
  }}
}}
function endGame(){{
  gameOver=true;
  document.getElementById('final').textContent=score;
  document.getElementById('over').style.display='block';
}}
function draw(){{
  X.fillStyle=COLORS.bg;X.fillRect(0,0,W,H);
  for(let p of platforms){{
    X.fillStyle=COLORS.plat;X.beginPath();
    X.roundRect(p.x,p.y,p.w,p.h,4);X.fill();
  }}
  for(let c of coins){{
    if(c.collected)continue;
    X.fillStyle=COLORS.coin;
    X.beginPath();X.arc(c.x+c.w/2,c.y+c.h/2,8,0,Math.PI*2);X.fill();
    X.fillStyle='#fff';X.font='10px Arial';X.textAlign='center';X.fillText('$',c.x+c.w/2,c.y+c.h/2+4);
  }}
  X.fillStyle=COLORS.player;X.beginPath();
  X.roundRect(player.x,player.y,player.w,player.h,4);X.fill();
  X.fillStyle='rgba(255,255,255,0.3)';
  X.fillRect(player.x+4,player.y+4,player.w-8,6);
}}
document.addEventListener('keydown',e=>{{keys[e.code]=true;if(gameOver&&(e.code==='Enter'||e.code==='Space'))init();}});
document.addEventListener('keyup',e=>{{keys[e.code]=false;}});
init();
</script>
</body>
</html>"""


def _build_shooter(spec: dict) -> str:
    colors = spec.get("colors", {})
    bg = colors.get("bg", "#0a0a1a")
    pc = colors.get("player", "#00f0f0")
    ec = colors.get("enemy", "#e94560")
    bc = colors.get("bullet", "#ffd700")
    title = spec.get("title", "Space Shooter")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{bg};display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif;color:#fff}}
canvas{{border:2px solid {ec}44;border-radius:4px;display:block}}
.game-container{{text-align:center}}
h1{{color:{pc};margin-bottom:12px}}
.info{{font-size:16px;margin:8px 0}} .info span{{color:{bc};font-weight:bold}}
.lives span{{color:{pc}}}
.game-over{{color:{ec};font-size:20px;margin-top:8px;display:none}}
button{{padding:10px 24px;font-size:16px;background:{ec};color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}}
button:hover{{opacity:0.85}}
</style>
</head>
<body>
<div class="game-container">
<h1>{title}</h1>
<div class="info">Score: <span id="score">0</span> | <span class="lives">Lives: <span id="lives">3</span></span></div>
<canvas id="game" width="480" height="640"></canvas>
<div class="game-over" id="over">Game Over! Score: <span id="final"></span></div>
<button onclick="init()">New Game</button>
</div>
<script>
const C=document.getElementById('game'),X=C.getContext('2d');
const W=480,H=640;
let player,bullets,enemies,score,lives,gameOver,keys={{}},frame=0,anim;
function init(){{
  player={{x:W/2-20,y:H-60,w:40,h:40}};
  bullets=[];enemies=[];score=0;lives=3;gameOver=false;frame=0;
  document.getElementById('score').textContent='0';document.getElementById('lives').textContent='3';
  document.getElementById('over').style.display='none';
  if(anim)cancelAnimationFrame(anim);tick();
}}
function spawnEnemy(){{
  let size=20+Math.random()*20;
  enemies.push({{x:Math.random()*(W-size),y:-size,w:size,h:size,speed:1+Math.random()*2,hp:1}});
}}
function tick(){{
  update();draw();
  if(!gameOver)anim=requestAnimationFrame(tick);
}}
function update(){{
  frame++;
  if(frame%30===0)spawnEnemy();
  let dx=0;
  if(keys['ArrowLeft']||keys['KeyA'])dx=-5;
  if(keys['ArrowRight']||keys['KeyD'])dx=5;
  player.x=Math.max(0,Math.min(W-player.w,player.x+dx));
  if(keys['Space']&&frame%10===0){{
    bullets.push({{x:player.x+player.w/2-3,y:player.y-10,w:6,h:16,speed:-8}});
  }}
  for(let i=bullets.length-1;i>=0;i--){{
    let b=bullets[i];b.y+=b.speed;
    if(b.y+b.h<0){{bullets.splice(i,1);continue;}}
    let hit=false;
    for(let j=enemies.length-1;j>=0;j--){{
      let e=enemies[j];
      if(b.x<e.x+e.w&&b.x+b.w>e.x&&b.y<e.y+e.h&&b.y+b.h>e.y){{
        e.hp--;bullets.splice(i,1);hit=true;
        if(e.hp<=0){{enemies.splice(j,1);score+=10;document.getElementById('score').textContent=score;}}
        break;
      }}
    }}
    if(hit)continue;
  }}
  for(let i=enemies.length-1;i>=0;i--){{
    let e=enemies[i];e.y+=e.speed;
    if(e.y>H){{enemies.splice(i,1);continue;}}
    if(player.x<e.x+e.w&&player.x+player.w>e.x&&player.y<e.y+e.h&&player.y+player.h>e.y){{
      enemies.splice(i,1);lives--;document.getElementById('lives').textContent=lives;
      if(lives<=0){{endGame();return;}}
    }}
  }}
}}
function endGame(){{
  gameOver=true;
  document.getElementById('final').textContent=score;
  document.getElementById('over').style.display='block';
}}
function draw(){{
  X.fillStyle='{bg}';X.fillRect(0,0,W,H);
  for(let s of [...Array(40).keys()]){{let y=(s*16+frame*2)%(H+32)-16;X.fillStyle='rgba(255,255,255,0.'+(Math.floor(s%5)+1)+')';X.fillRect(s%W*12,y,1.5,1.5);}}
  for(let b of bullets){{X.fillStyle='{bc}';X.fillRect(b.x,b.y,b.w,b.h);}}
  for(let e of enemies){{X.fillStyle='{ec}';X.beginPath();let cx=e.x+e.w/2,cy=e.y+e.h/2,r=e.w/2;for(let i=0;i<6;i++){{let a=i*Math.PI/3-Math.PI/2;let rr=i%2===0?r:r*0.6;i===0?X.moveTo(cx+Math.cos(a)*rr,cy+Math.sin(a)*rr):X.lineTo(cx+Math.cos(a)*rr,cy+Math.sin(a)*rr);}}X.closePath();X.fill();}}
  X.fillStyle='{pc}';X.beginPath();
  X.moveTo(player.x+player.w/2,player.y);X.lineTo(player.x+player.w,player.y+player.h);
  X.lineTo(player.x+player.w-8,player.y+player.h-8);X.lineTo(player.x+8,player.y+player.h-8);
  X.lineTo(player.x,player.y+player.h);X.closePath();X.fill();
  X.fillStyle='rgba(255,255,255,0.2)';X.fillRect(player.x+12,player.y+6,16,4);
}}
document.addEventListener('keydown',e=>{{keys[e.code]=true;if(gameOver&&(e.code==='Enter'||e.code==='Space'))init();}});
document.addEventListener('keyup',e=>{{keys[e.code]=false;}});
init();
</script>
</body>
</html>"""


def _build_racing(spec: dict) -> str:
    colors = spec.get("colors", {})
    bg = colors.get("bg", "#1a1a2e")
    pc = colors.get("player", "#e94560")
    oc = colors.get("obstacle", "#0f3460")
    rc = colors.get("road", "#16213e")
    title = spec.get("title", "Racer")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{bg};display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif;color:#fff}}
canvas{{border:2px solid {rc};border-radius:4px;display:block}}
.game-container{{text-align:center}}
h1{{color:{pc};margin-bottom:12px}}
.info{{font-size:16px;margin:8px 0}} .info span{{color:{pc};font-weight:bold}}
.game-over{{color:{pc};font-size:20px;margin-top:8px;display:none}}
button{{padding:10px 24px;font-size:16px;background:{pc};color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}}
button:hover{{opacity:0.85}}
.hint{{color:#888;font-size:13px;margin-top:6px}}
</style>
</head>
<body>
<div class="game-container">
<h1>{title}</h1>
<div class="info">Score: <span id="score">0</span></div>
<canvas id="game" width="400" height="600"></canvas>
<div class="game-over" id="over">Game Over! Score: <span id="final"></span></div>
<button onclick="init()">New Game</button>
<div class="hint">&larr;&rarr; or A/D to steer</div>
</div>
<script>
const C=document.getElementById('game'),X=C.getContext('2d');
const W=400,H=600;
let player,obstacles,score,speed,gameOver,keys={{}},roadOffset=0,anim;
function init(){{
  player={{x:W/2-20,y:H-80,w:40,h:60}};
  obstacles=[];score=0;speed=5;gameOver=false;roadOffset=0;
  document.getElementById('score').textContent='0';document.getElementById('over').style.display='none';
  if(anim)cancelAnimationFrame(anim);tick();
}}
function tick(){{
  update();draw();
  if(!gameOver)anim=requestAnimationFrame(tick);
}}
function update(){{
  roadOffset=(roadOffset+speed)%80;
  if(Math.random()<0.02*{1.5}){{
    let lane=Math.floor(Math.random()*3);
    obstacles.push({{x:40+lane*110,y:-60,w:60,h:60}});
  }}
  let dx=0;
  if(keys['ArrowLeft']||keys['KeyA'])dx=-5;
  if(keys['ArrowRight']||keys['KeyD'])dx=5;
  player.x=Math.max(10,Math.min(W-player.w-10,player.x+dx));
  for(let i=obstacles.length-1;i>=0;i--){{
    let o=obstacles[i];o.y+=speed;
    if(o.y>H){{obstacles.splice(i,1);score+=5;document.getElementById('score').textContent=score;speed=5+Math.floor(score/50);continue;}}
    if(player.x<o.x+o.w&&player.x+player.w>o.x&&player.y<o.y+o.h&&player.y+player.h>o.y){{endGame();return;}}
  }}
}}
function endGame(){{
  gameOver=true;
  document.getElementById('final').textContent=score;
  document.getElementById('over').style.display='block';
}}
function draw(){{
  X.fillStyle='{rc}';X.fillRect(0,0,W,H);
  for(let i=0;i<10;i++){{let y=(i*80+roadOffset)%(H+80)-40;X.fillStyle='rgba(255,255,255,0.1)';X.fillRect(30,40+i*80,340,40);X.fillStyle='rgba(255,255,255,0.15)';X.fillRect(30,y,340,40);X.fillStyle='#fff';X.fillRect(195,y+16,10,8);}}
  for(let o of obstacles){{X.fillStyle='{oc}';X.beginPath();X.roundRect(o.x,o.y,o.w,o.h,8);X.fill();X.fillStyle='rgba(255,255,255,0.2)';X.fillRect(o.x+8,o.y+8,o.w-16,8);}}
  X.fillStyle='{pc}';X.beginPath();X.roundRect(player.x,player.y,player.w,player.h,8);X.fill();
  X.fillStyle='rgba(255,255,255,0.3)';X.fillRect(player.x+8,player.y+8,player.w-16,12);
  X.fillStyle='rgba(255,255,255,0.4)';X.fillRect(player.x+8,player.y+player.h-20,player.w-16,8);
}}
document.addEventListener('keydown',e=>{{keys[e.code]=true;if(gameOver&&(e.code==='Enter'||e.code==='Space'))init();}});
document.addEventListener('keyup',e=>{{keys[e.code]=false;}});
init();
</script>
</body>
</html>"""


def _build_puzzle(spec: dict) -> str:
    colors = spec.get("colors", {})
    bg = colors.get("bg", "#1a1a2e")
    pc = colors.get("primary", "#e94560")
    sc = colors.get("secondary", "#4ecca3")
    title = spec.get("title", "Match-3 Puzzle")
    grid_size = 8
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{bg};display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:Arial,sans-serif;color:#fff}}
canvas{{border:2px solid {sc};border-radius:4px;display:block}}
.game-container{{text-align:center}}
h1{{color:{pc};margin-bottom:12px}}
.info{{font-size:16px;margin:8px 0}} .info span{{color:{sc};font-weight:bold}}
.game-over{{color:{pc};font-size:20px;margin-top:8px;display:none}}
button{{padding:10px 24px;font-size:16px;background:{pc};color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:8px}}
button:hover{{opacity:0.85}}
</style>
</head>
<body>
<div class="game-container">
<h1>{title}</h1>
<div class="info">Score: <span id="score">0</span> | Moves: <span id="moves">30</span></div>
<canvas id="game" width="400" height="400"></canvas>
<div class="game-over" id="over">Game Over! Score: <span id="final"></span></div>
<button onclick="init()">New Game</button>
</div>
<script>
const C=document.getElementById('game'),X=C.getContext('2d');
const S=8,T=50,G=2,O=400;
let grid,score,moves,selected,gameOver,animating=false;
const GEMS=['{pc}','{sc}','#f5a623','#a000f0','#00f0f0','#f0f000'];
function init(){{
  grid=[];score=0;moves=30;selected=null;gameOver=false;
  for(let r=0;r<S;r++){{grid[r]=[];for(let c=0;c<S;c++)grid[r][c]=Math.floor(Math.random()*GEMS.length);}}
  while( findMatches().length>0 ) resolveMatches();
  document.getElementById('score').textContent='0';document.getElementById('moves').textContent='30';
  document.getElementById('over').style.display='none';
  draw();
}}
function findMatches(){{
  let matches=[];
  for(let r=0;r<S;r++)for(let c=0;c<S-2;c++){{let v=grid[r][c];if(v>=0&&v===grid[r][c+1]&&v===grid[r][c+2])matches.push(...[r,c,r,c+1,r,c+2]);}}
  for(let c=0;c<S;c++)for(let r=0;r<S-2;r++){{let v=grid[r][c];if(v>=0&&v===grid[r+1][c]&&v===grid[r+2][c])matches.push(...[r,c,r+1,c,r+2,c]);}}
  return [...new Set(matches)];
}}
function resolveMatches(){{
  let m=findMatches();
  while(m.length>0){{
    for(let i=0;i<m.length;i+=2)grid[m[i]][m[i+1]]=-1;
    for(let c=0;c<S;c++){{let col=[];for(let r=S-1;r>=0;r--)if(grid[r][c]>=0)col.push(grid[r][c]);while(col.length<S)col.unshift(Math.floor(Math.random()*GEMS.length));for(let r=0;r<S;r++)grid[r][c]=col[r];}}
    m=findMatches();
  }}
}}
function swap(r1,c1,r2,c2){{let t=grid[r1][c1];grid[r1][c1]=grid[r2][c2];grid[r2][c2]=t;}}
function click(px,py){{
  if(gameOver||animating)return;
  let c=Math.floor(px/T),r=Math.floor(py/T);
  if(c<0||c>=S||r<0||r>=S)return;
  if(selected===null){{selected={{r,c}};draw();return;}}
  let dr=Math.abs(r-selected.r),dc=Math.abs(c-selected.c);
  if((dr===1&&dc===0)||(dr===0&&dc===1)){{
    swap(selected.r,selected.c,r,c);
    if(findMatches().length>0){{resolveMatches();score+=10;moves--;document.getElementById('score').textContent=score;document.getElementById('moves').textContent=moves;if(moves<=0)gameOver=true;}}
    else swap(selected.r,selected.c,r,c);
  }}
  if(gameOver){{document.getElementById('final').textContent=score;document.getElementById('over').style.display='block';}}
  selected=null;draw();
}}
function draw(){{
  X.fillStyle='{bg}';X.fillRect(0,0,O,O);
  for(let r=0;r<S;r++)for(let c=0;c<S;c++){{
    if(grid[r][c]<0)continue;
    X.fillStyle=GEMS[grid[r][c]%GEMS.length];
    X.beginPath();X.roundRect(c*T+2,r*T+2,T-4,T-4,6);X.fill();
    if(selected&&selected.r===r&&selected.c===c){{X.strokeStyle='#fff';X.lineWidth=3;X.beginPath();X.roundRect(c*T+2,r*T+2,T-4,T-4,6);X.stroke();}}
  }}
}}
C.onclick=e=>{{let r=C.getBoundingClientRect();click(e.clientX-r.left,e.clientY-r.top);}};
init();
</script>
</body>
</html>"""


_GAME_BUILDERS = {
    "platformer": _build_platformer,
    "shooter": _build_shooter,
    "racing": _build_racing,
    "puzzle": _build_puzzle,
}


async def artifact_create_game_from_spec(spec_json: str) -> dict:
    """Create a complete HTML5 game from a JSON specification.

    Parameters
    ----------
    spec_json : JSON string describing the game genre, colors, mechanics
    """
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid spec_json: {e}"}

    genre = spec.get("genre", "platformer").lower()
    builder = _GAME_BUILDERS.get(genre)
    if not builder:
        return {
            "success": False,
            "error": f"Unsupported genre: {genre}. Supported: {', '.join(_GAME_BUILDERS)}",
        }

    try:
        html = builder(spec)
        title = spec.get("title", f"{genre.title()} Game")
        return _save_artifact(html, title, "game_spec", {"genre": genre})
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SVG generation from description
# ---------------------------------------------------------------------------

def _parse_svg_desc(desc: str) -> dict:
    desc_lower = desc.lower()
    shape = "circle"
    if any(w in desc_lower for w in ["rectangle", "rect", "square", "box"]):
        shape = "rect"
    elif any(w in desc_lower for w in ["ellipse", "oval"]):
        shape = "ellipse"
    elif any(w in desc_lower for w in ["line", "path", "curve"]):
        shape = "path"
    elif any(w in desc_lower for w in ["triangle", "polygon"]):
        shape = "polygon"
    elif any(w in desc_lower for w in ["text", "label", "title", "heading"]):
        shape = "text"
    elif any(w in desc_lower for w in ["chart", "bar", "graph", "plot"]):
        shape = "chart"
    elif any(w in desc_lower for w in ["logo", "icon", "brand"]):
        shape = "logo"

    colors = []
    named_colors = {
        "red": "#e94560", "blue": "#3498db", "green": "#2ecc71", "yellow": "#ffd700",
        "orange": "#f39c12", "purple": "#9b59b6", "pink": "#ff6b9d", "black": "#1a1a2e",
        "white": "#ffffff", "gray": "#888888", "grey": "#888888", "teal": "#1abc9c",
        "cyan": "#00f0f0", "indigo": "#4b0082", "violet": "#8e44ad", "brown": "#8b4513",
        "gold": "#ffd700", "silver": "#c0c0c0"
    }
    for name, hexv in named_colors.items():
        if name in desc_lower:
            colors.append(hexv)
    if not colors:
        colors = ["#3498db", "#2ecc71", "#e94560"]

    has_border = any(w in desc_lower for w in ["border", "outline", "stroke", "frame"])
    has_gradient = any(w in desc_lower for w in ["gradient", "fade", "shiny"])
    has_shadow = any(w in desc_lower for w in ["shadow", "drop"])
    has_text = any(w in desc_lower for w in ["text", "label", "word", "name"])
    has_pattern = any(w in desc_lower for w in ["pattern", "striped", "dotted", "dashed"])
    is_3d = any(w in desc_lower for w in ["3d", "isometric", "cube", "three-dimensional"])

    return {
        "shape": shape,
        "colors": colors,
        "has_border": has_border,
        "has_gradient": has_gradient,
        "has_shadow": has_shadow,
        "has_text": has_text,
        "has_pattern": has_pattern,
        "is_3d": is_3d,
    }


def _gen_svg_shape(parsed: dict, style: str, desc: str) -> str:
    cols = parsed["colors"]
    grad_defs = ""
    defs = ""
    body = ""

    if parsed["has_gradient"]:
        grad_defs = f"""<defs>
<linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" style="stop-color:{cols[0]}"/>
<stop offset="100%" style="stop-color:{cols[1] if len(cols)>1 else cols[0]}"/>
</linearGradient>
</defs>"""
        fill = "url(#g1)"
    else:
        fill = cols[0]

    if parsed["has_shadow"]:
        defs += f"""<filter id="shadow"><feDropShadow dx="2" dy="4" stdDeviation="4" flood-opacity="0.3"/></filter>"""
        filt = 'filter="url(#shadow)"'
    else:
        filt = ""

    border = f'stroke="{cols[1] if len(cols)>1 else "#333"}" stroke-width="3"' if parsed["has_border"] else ""

    if parsed["shape"] == "rect":
        body = f'<rect x="100" y="100" width="250" height="180" rx="12" fill="{fill}" {border} {filt}/>'
    elif parsed["shape"] == "ellipse":
        body = f'<ellipse cx="250" cy="200" rx="180" ry="120" fill="{fill}" {border} {filt}/>'
    elif parsed["shape"] == "polygon":
        body = f'<polygon points="250,60 400,340 100,340" fill="{fill}" {border} {filt}/>'
    elif parsed["shape"] == "path":
        body = f'<path d="M100,300 Q200,100 300,200 T500,150" fill="none" stroke="{cols[0]}" stroke-width="4" {filt}/>'
        if parsed["has_gradient"]:
            body = f'<path d="M100,300 Q200,100 300,200 T500,150" fill="none" stroke="url(#g1)" stroke-width="4" {filt}/>'
    elif parsed["shape"] == "chart":
        bars = ""
        bar_data = [120, 200, 160, 280, 220, 310, 180]
        bw = 50
        gap = 20
        base = 400
        for i, v in enumerate(bar_data):
            x = 60 + i * (bw + gap)
            h = v
            c = cols[i % len(cols)]
            bars += f'<rect x="{x}" y="{base - h}" width="{bw}" height="{h}" rx="4" fill="{c}"/>'
        body = f"""<text x="250" y="40" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">Chart</text>
<line x1="40" y1="50" x2="40" y2="420" stroke="#ccc" stroke-width="2"/>
<line x1="40" y1="420" x2="480" y2="420" stroke="#ccc" stroke-width="2"/>
{bars}"""
    elif parsed["shape"] == "logo":
        body = f"""<circle cx="250" cy="180" r="80" fill="url(#g1)" {filt}/>
<text x="250" y="380" text-anchor="middle" font-size="36" font-weight="bold" fill="{cols[0]}">BRAND</text>
<rect x="180" y="340" width="140" height="3" rx="1.5" fill="{cols[1] if len(cols)>1 else cols[0]}"/>"""
        if not parsed["has_gradient"]:
            body = body.replace('fill="url(#g1)"', f'fill="{cols[0]}"')
    elif parsed["shape"] == "text":
        body = f'<text x="250" y="220" text-anchor="middle" font-size="48" font-weight="bold" fill="{cols[0]}" {filt}>Sample Text</text>'
    else:
        body = f'<circle cx="250" cy="200" r="120" fill="{fill}" {border} {filt}/>'

    if parsed["has_pattern"]:
        defs += """<pattern id="p1" patternUnits="userSpaceOnUse" width="20" height="20">
<rect width="20" height="20" fill="none"/>
<line x1="0" y1="0" x2="20" y2="20" stroke="rgba(255,255,255,0.15)" stroke-width="2"/>
</pattern>"""
        body = body.replace(f'fill="{fill}"', f'fill="url(#p1)"')

    if parsed["has_text"] and parsed["shape"] not in ("text", "logo", "chart"):
        body += f'\n<text x="250" y="440" text-anchor="middle" font-size="20" fill="{cols[0]}">{desc[:40]}</text>'

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
{grad_defs}
{defs}
{body}
</svg>"""
    return svg_content


async def artifact_create_svg_from_desc(description: str, style: str = "modern") -> dict:
    """Create an SVG graphic from a natural language description.

    Parameters
    ----------
    description : text description of the desired SVG
    style : modern, flat, minimal, detailed, isometric
    """
    if not description:
        return {"success": False, "error": "Description cannot be empty"}

    try:
        parsed = _parse_svg_desc(description)
        svg_content = _gen_svg_shape(parsed, style, description)
        title = f"SVG: {description[:40]}"
        body = f'<div style="display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f5f5f5">{svg_content}</div>'
        full = _wrap_html(title, body)
        return _save_artifact(full, title, "svg_desc", {"svg_content": svg_content, "style": style})
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Dashboard generation
# ---------------------------------------------------------------------------

def _build_dashboard_chart(data: list, chart_type: str, width: int, height: int, colors: list) -> str:
    max_val = max(data) if data else 1
    canvas_id = f"chart_{uuid.uuid4().hex[:6]}"
    js = ""
    if chart_type == "bar":
        js = f"""var c=document.getElementById('{canvas_id}'),x=c.getContext('2d'),w={width},h={height};
c.width=w;c.height=h;
x.fillStyle='transparent';x.fillRect(0,0,w,h);
var d={json.dumps(data)},cl={json.dumps(colors)},max={max_val},bw=Math.max(10,(w-40)/d.length-6);
d.forEach(function(v,i){{var bh=(v/max)*(h-40),clr=cl[i%cl.length];
x.fillStyle=clr;x.beginPath();x.roundRect(20+i*(bw+8),h-20-bh,bw,bh,[3,3,0,0]);x.fill();
x.fillStyle='#888';x.font='10px Arial';x.textAlign='center';x.fillText(v,20+i*(bw+8)+bw/2,h-8);}});"""
    elif chart_type == "line":
        js = f"""var c=document.getElementById('{canvas_id}'),x=c.getContext('2d'),w={width},h={height};
c.width=w;c.height=h;
x.fillStyle='transparent';x.fillRect(0,0,w,h);
var d={json.dumps(data)},cl={json.dumps(colors)},max={max_val};
x.strokeStyle=cl[0];x.lineWidth=2.5;x.beginPath();
d.forEach(function(v,i){{var px=20+i*(w-40)/(d.length-1),py=h-20-(v/max)*(h-40);
i===0?x.moveTo(px,py):x.lineTo(px,py);}});x.stroke();
d.forEach(function(v,i){{var px=20+i*(w-40)/(d.length-1),py=h-20-(v/max)*(h-40);
x.fillStyle=cl[0];x.beginPath();x.arc(px,py,4,0,Math.PI*2);x.fill();
x.fillStyle='#fff';x.beginPath();x.arc(px,py,2,0,Math.PI*2);x.fill();}});"""
    elif chart_type == "pie":
        js = f"""var c=document.getElementById('{canvas_id}'),x=c.getContext('2d'),w={width},h={height};
c.width=w;c.height=h;
x.fillStyle='transparent';x.fillRect(0,0,w,h);
var d={json.dumps(data)},cl={json.dumps(colors)},total=d.reduce(function(a,b){{return a+b;}},0),start=0;
d.forEach(function(v,i){{var a=(v/total)*Math.PI*2;
x.fillStyle=cl[i%cl.length];x.beginPath();x.moveTo(w/2,h/2);x.arc(w/2,h/2,Math.min(w,h)/2-20,start,start+a);x.closePath();x.fill();
var mid=start+a/2;x.fillStyle='#fff';x.font='11px Arial';x.textAlign='center';
x.fillText(Math.round(v/total*100)+'%',w/2+Math.cos(mid)*Math.min(w,h)/3,h/2+Math.sin(mid)*Math.min(w,h)/3);
start+=a;}});"""
    return f"<canvas id='{canvas_id}' style='width:100%;height:{height}px'></canvas><script>{js}</script>"


async def artifact_create_dashboard(title: str, widgets_json: str) -> dict:
    """Create a full HTML dashboard with drag-and-resize widgets.

    Parameters
    ----------
    title : dashboard title
    widgets_json : JSON string describing widgets (metric, chart, table, text)
    """
    try:
        widgets = json.loads(widgets_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid widgets_json: {e}"}

    if not isinstance(widgets, list):
        return {"success": False, "error": "widgets_json must be a JSON array"}

    try:
        chart_colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"]
        cards_html = []
        for i, w in enumerate(widgets):
            wtype = w.get("type", "text")
            wtitle = w.get("title", f"Widget {i+1}")
            wid = f"w_{uuid.uuid4().hex[:6]}"

            if wtype == "metric":
                value = w.get("value", "—")
                change = w.get("change", "")
                change_cls = "up" if change.startswith("+") else "down" if change.startswith("-") else ""
                cards_html.append(f"""<div class="widget-card metric-card" id="{wid}"><div class="widget-header">{wtitle}</div><div class="metric-value">{value}</div><div class="metric-change {change_cls}">{change}</div></div>""")

            elif wtype == "chart":
                chart_type = w.get("chart_type", "bar")
                data = w.get("data", [10, 20, 15, 30, 25])
                chart_html = _build_dashboard_chart(data, chart_type, 400, 200, chart_colors)
                cards_html.append(f"""<div class="widget-card chart-card" id="{wid}"><div class="widget-header">{wtitle}</div><div class="widget-content">{chart_html}</div></div>""")

            elif wtype == "table":
                headers = w.get("headers", ["Col 1", "Col 2"])
                rows = w.get("rows", [["—", "—"]])
                thead = "".join(f"<th>{h}</th>" for h in headers)
                tbody = "".join(f"<tr>{''.join(f'<td>{c}</td>' for c in row)}</tr>" for row in rows)
                cards_html.append(f"""<div class="widget-card table-card" id="{wid}"><div class="widget-header">{wtitle}</div><div class="widget-content"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div></div>""")

            else:
                content = w.get("content", "")
                cards_html.append(f"""<div class="widget-card text-card" id="{wid}"><div class="widget-header">{wtitle}</div><div class="widget-content"><p>{content}</p></div></div>""")

        css = f""":root{{--primary:#3498db;--bg:#f0f2f5;--card-bg:#fff;--text:#1a1a2e;--text-muted:#666;--border:rgba(0,0,0,0.08);--radius:10px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);padding:20px}}
.dashboard-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}}
.dashboard-header h1{{font-size:1.5rem}}
.dashboard-header .ts{{color:var(--text-muted);font-size:0.85rem}}
.widget-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.widget-card{{background:var(--card-bg);border-radius:var(--radius);border:1px solid var(--border);overflow:hidden;transition:box-shadow .2s}}
.widget-card:hover{{box-shadow:0 4px 12px rgba(0,0,0,0.06)}}
.widget-header{{padding:14px 16px;font-weight:600;font-size:0.95rem;border-bottom:1px solid var(--border);background:rgba(0,0,0,0.02)}}
.widget-content{{padding:16px}}
.metric-card{{text-align:center;padding:24px 16px}}
.metric-value{{font-size:2.5rem;font-weight:700;margin:8px 0;color:var(--text)}}
.metric-change{{font-size:1rem;font-weight:500}}
.metric-change.up{{color:#2ecc71}}
.metric-change.down{{color:#e74c3c}}
table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border)}}
th{{font-weight:600;color:var(--text-muted);font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px}}
tbody tr:hover{{background:rgba(0,0,0,0.02)}}
.chart-card canvas{{display:block;margin:0 auto}}
.text-card p{{line-height:1.6;color:var(--text-muted)}}"""

        body = f"""<div class="dashboard-header"><h1>{title}</h1><span class="ts">{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</span></div><div class="widget-grid">{"".join(cards_html)}</div>"""
        full = _wrap_html(title, body, css)
        return _save_artifact(full, title, "dashboard", {"type": "dashboard"})
    except Exception as e:
        return {"success": False, "error": str(e)}
