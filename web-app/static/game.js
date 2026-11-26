const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const scoreVal = document.getElementById("scoreVal");
const statusText = document.getElementById("statusText")

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

//changing controls based on game mode gesture or manual(used to test the game before add gesture)

if(GAME_MODE === "manual"){
    canvas.addEventListener("mousedown", () => isSlicing = true);
    canvas.addEventListener("mouseup", () => isSlicing = false);
    canvas.addEventListener("mouseleave", () => isSlicing = false);
    canvas.addEventListener("mousemove", (e) => {
        if (isSlicing) {
            bladeTrail.push({x: e.clientX, y: e.clientY});
        }
    });
}
//gesture control
else if (GAME_MODE === "gesture") {
    const video = document.getElementById("webcam");
    const hiddenCanvas = document.getElementById("hiddenCanvas");
    const hiddenCtx = hiddenCanvas.getContext("2d");

    hiddenCanvas.width = 320;
    hiddenCanvas.height = 240;

    async function startCamera() {
        try{
            const stream = await navigator.mediaDevices.getUserMedia({ video: true});
        
        video.srcObject = stream;
        statusText.innerText = "slice using your index finger"
        setInterval(sendFrameToML, 100);
        }catch (err) {
            statusText.innerText = "camera unaccessable";
        }
    }

    let frameId = 0;
    const sessionId = "session_" + Date.now();
    let isSendingFrame = false;

    async function sendFrameToML() {
        if (video.readyState !== video.HAVE_ENOUGH_DATA){
            return;
        }
        if (isSendingFrame){
            return;
        }

        isSendingFrame = true;

        hiddenCtx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
        
        hiddenCanvas.toBlob(async (blob) => {
            if (!blob){
                isSendingFrame=false;
                return;
            }

            const formData = new FormData();
            formData.append("frame", blob, "frame.jpg");
            formData.append("frame_id", frameId++);
            formData.append("session_id", sessionId);

            try{
                const response = await fetch('/api/track',{
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.found){
                    isSlicing=true;
                    statusText.innerText=`Tracking! (${data.inference_ms}ms)`;

                    bladeTrail.push({
                        x: data.x * canvas.width,
                        y: data.y * canvas.height
                    });
                }
                else{
                    isSlicing=false;
                    statusText.innerText = "show your hand";
                }
            } catch(error){
                console.log("ml tracker is offline");
            }finally{
                isSendingFrame = false;
            }
        }, "image/jpeg", 0.5);
    }
    startCamera();
}



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
            this.x = this.radius;
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
        ctx.strokeStyle = GAME_MODE === "gesture" ? "#00ffcc" : "#007bff";
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