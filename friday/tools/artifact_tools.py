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
