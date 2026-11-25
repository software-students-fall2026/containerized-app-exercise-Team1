const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const scoreVal = document.getElementById("scoreVal");

let score = 0;
let fruits = [];
let bladeTrail = [];
let isSlicing = false;

const fruitEmojis = ["🍎", "🍏", "🍋", "🍊", "🍑", "🍇", "🍐", "🍈"]

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

canvas.addEventListener("mousedown", () => isSlicing = true);
canvas.addEventListener("mouseup", () => isSlicing = false);
canvas.addEventListener("mouseleave", () => isSlicing = false);
canvas.addEventListener("mousemove", (e) => {
    if (isSlicing) {
        bladeTrail.push({x: e.clientX, y: e.clientY});
    }
});

class Fruit {
    constructor() {
        this.x = Math.random() * (canvas.width - 100) + 50;
        this.y = canvas.height + 50;

        this.vx = (Math.random() - 0.5) * 8;

        const jumpHeight = canvas.height * 0.7;
        this.gravity = 0.15;
        this.vy = -Math.sqrt(2 * this.gravity * jumpHeight);

        this.radius = 40;
        this.emoji = fruitEmojis[Math.floor(Math.random() * fruitEmojis.length)];
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;
        this.vy += this.gravity;

        if(this.x - this.radius < 0){
            this.x - this.radius;
            this.vx = Math.abs(this.vx);
        }
        else if(this.x + this.radius > canvas.width){
            this.x = canvas.width - this.radius;
            this.vx = -Math.abs(this.vx)
        }
    }

    draw() {
        ctx.font = `${this.radius * 2}px Arial`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(this.emoji, this.x, this.y);
    }
}

setInterval(() => {
    fruits.push(new Fruit());
}, 800);

function gameLoop(){
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = fruits.length - 1; i>= 0; i--){
        let f = fruits[i];
        f.update();
        f.draw();

        if (f.y > canvas.height + 100){
            fruits.splice(i, 1);
            continue;
        }

        if (isSlicing && bladeTrail.length>0){
            let currentBladePos = bladeTrail[bladeTrail.length-1];
            let distance = Math.hypot(f.x-currentBladePos.x, f.y - currentBladePos.y);
            
            if (distance < f.radius + 20) {
                fruits.splice(i, 1);
                score+=10;
                scoreVal.innerText = score;
            }
        }
    }

    if(bladeTrail.length > 0) {
        ctx.beginPath();
        ctx.moveTo(bladeTrail[0].x, bladeTrail[0].y);
        for (let i = 1; i<bladeTrail.length; i++){
            ctx.lineTo(bladeTrail[i].x, bladeTrail[i].y);
        }
        ctx.strokeStyle = "#00ffcc";
        ctx.lineWidth = 5;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.stroke();
    }

    if (bladeTrail.length > 5){
        bladeTrail.shift();
    }
    else if (!isSlicing) {
        bladeTrail = [];
    }
    requestAnimationFrame(gameLoop);
}

gameLoop()