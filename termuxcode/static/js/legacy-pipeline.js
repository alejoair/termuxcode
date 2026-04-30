// ===== Pipeline Background Effect =====
// Based on: https://github.com/crnacura/AmbientCanvasBackgrounds

const { PI, cos, sin, abs, sqrt, pow, round, random, atan2 } = Math;
const HALF_PI = 0.5 * PI;
const TAU = 2 * PI;
const TO_RAD = PI / 180;
const floor = n => n | 0;
const rand = n => n * random();
const fadeInOut = (t, m) => {
    let hm = 0.5 * m;
    return abs((t + hm) % m - hm) / (hm);
};

export function initPipeline() {
    // Config
    const IDLE = {
        pipeCount: 30,
        baseSpeed: 0.2,
        rangeSpeed: 0.4,
        baseHue: 180,
        rangeHue: 60,
        backgroundColor: '#000000',
        blur: 12
    };
    const WORK = {
        pipeCount: 60,
        baseSpeed: 1.5,
        rangeSpeed: 2.5,
        baseHue: 220,
        rangeHue: 80,
        backgroundColor: '#000000',
        blur: 16
    };

    let container, canvas, ctx, center, tick, pipeProps;
    let pipeCount = IDLE.pipeCount;
    const pipePropCount = 8;
    let pipePropsLength = pipeCount * pipePropCount;
    const turnCount = 8;
    const turnAmount = (360 / turnCount) * TO_RAD;
    const turnChanceRange = 58;
    const baseWidth = 2;
    const rangeWidth = 4;
    const baseTTL = 100;
    const rangeTTL = 300;
    const FADE_ALPHA = 0.04; // Velocidad de desvanecimiento (mayor = líneas más cortas)

    let working = false;
    let transitionProgress = 0;
    const TRANSITION_SPEED = 0.02;

    function lerp(a, b, t) { return a + (b - a) * t; }

    function createCanvas() {
        container = document.body;
        canvas = {
            a: document.createElement('canvas'),
            b: document.createElement('canvas')
        };
        canvas.b.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.85;
        `;
        container.appendChild(canvas.b);
        ctx = {
            a: canvas.a.getContext('2d'),
            b: canvas.b.getContext('2d')
        };
        center = [];
        tick = 0;
    }

    function resize() {
        const { innerWidth, innerHeight } = window;

        canvas.a.width = innerWidth;
        canvas.a.height = innerHeight;

        ctx.a.drawImage(canvas.b, 0, 0);

        canvas.b.width = innerWidth;
        canvas.b.height = innerHeight;

        ctx.b.drawImage(canvas.a, 0, 0);

        center[0] = 0.5 * canvas.a.width;
        center[1] = 0.5 * canvas.a.height;
    }

    function initPipes() {
        pipePropsLength = pipeCount * pipePropCount;
        pipeProps = new Float32Array(pipePropsLength);
        for (let i = 0; i < pipePropsLength; i += pipePropCount) {
            initPipe(i);
        }
    }

    function initPipe(i) {
        const t = transitionProgress;
        const baseSpeed = lerp(IDLE.baseSpeed, WORK.baseSpeed, t);
        const rangeSpeed = lerp(IDLE.rangeSpeed, WORK.rangeSpeed, t);
        const baseHue = lerp(IDLE.baseHue, WORK.baseHue, t);
        const rangeHue = lerp(IDLE.rangeHue, WORK.rangeHue, t);

        const x = rand(canvas.a.width);
        const y = center[1];
        const direction = (round(rand(1)) ? HALF_PI : TAU - HALF_PI);
        const speed = baseSpeed + rand(rangeSpeed);
        const life = 0;
        const ttl = baseTTL + rand(rangeTTL);
        const width = baseWidth + rand(rangeWidth);
        const hue = baseHue + rand(rangeHue);

        pipeProps.set([x, y, direction, speed, life, ttl, width, hue], i);
    }

    function updatePipes() {
        tick++;
        for (let i = 0; i < pipePropsLength; i += pipePropCount) {
            updatePipe(i);
        }
    }

    function updatePipe(i) {
        const i2 = 1 + i, i3 = 2 + i, i4 = 3 + i, i5 = 4 + i, i6 = 5 + i, i7 = 6 + i, i8 = 7 + i;

        let x = pipeProps[i];
        let y = pipeProps[i2];
        let direction = pipeProps[i3];
        const speed = pipeProps[i4];
        let life = pipeProps[i5];
        const ttl = pipeProps[i6];
        const width = pipeProps[i7];
        const hue = pipeProps[i8];

        drawPipe(x, y, life, ttl, width, hue);

        life++;
        x += cos(direction) * speed;
        y += sin(direction) * speed;

        const turnChance = !(tick % round(rand(turnChanceRange))) && (!(round(x) % 6) || !(round(y) % 6));
        const turnBias = round(rand(1)) ? -1 : 1;
        direction += turnChance ? turnAmount * turnBias : 0;

        pipeProps[i] = x;
        pipeProps[i2] = y;
        pipeProps[i3] = direction;
        pipeProps[i5] = life;

        // Wrap around edges
        if (x > canvas.a.width) pipeProps[i] = 0;
        if (x < 0) pipeProps[i] = canvas.a.width;
        if (y > canvas.a.height) pipeProps[i2] = 0;
        if (y < 0) pipeProps[i2] = canvas.a.height;

        life > ttl && initPipe(i);
    }

    function drawPipe(x, y, life, ttl, width, hue) {
        ctx.a.save();
        ctx.a.strokeStyle = `hsla(${hue}, 60%, 45%, ${fadeInOut(life, ttl) * 0.4})`;
        ctx.a.beginPath();
        ctx.a.arc(x, y, width, 0, TAU);
        ctx.a.stroke();
        ctx.a.closePath();
        ctx.a.restore();
    }

    function render() {
        const t = transitionProgress;
        const blur = lerp(IDLE.blur, WORK.blur, t);

        // Fade canvas.a rellenando con negro puro (OLED)
        ctx.a.save();
        ctx.a.fillStyle = `rgba(0, 0, 0, ${FADE_ALPHA})`;
        ctx.a.fillRect(0, 0, canvas.a.width, canvas.a.height);
        ctx.a.restore();

        ctx.b.save();
        ctx.b.fillStyle = '#000000';
        ctx.b.fillRect(0, 0, canvas.b.width, canvas.b.height);
        ctx.b.restore();

        ctx.b.save();
        ctx.b.filter = `blur(${blur}px)`;
        ctx.b.drawImage(canvas.a, 0, 0);
        ctx.b.restore();

        ctx.b.save();
        ctx.b.drawImage(canvas.a, 0, 0);
        ctx.b.restore();
    }

    function draw() {
        // Smooth transition between idle/work states
        if (working && transitionProgress < 1) {
            transitionProgress = Math.min(1, transitionProgress + TRANSITION_SPEED);
        } else if (!working && transitionProgress > 0) {
            transitionProgress = Math.max(0, transitionProgress - TRANSITION_SPEED);
        }

        updatePipes();
        render();
        requestAnimationFrame(draw);
    }

    // Update pipe count when transitioning
    function updatePipeCount() {
        const targetCount = working ? WORK.pipeCount : IDLE.pipeCount;
        if (targetCount !== pipeCount) {
            pipeCount = targetCount;
            initPipes();
        }
    }

    // Global setter for working state
    window.setPipelineWorking = function(val) {
        const wasWorking = working;
        working = !!val;
        if (working !== wasWorking) {
            updatePipeCount();
        }
    };

    // Also set starfield working for compatibility
    window.setStarfieldWorking = window.setPipelineWorking;

    function setup() {
        createCanvas();
        resize();
        initPipes();
        draw();
    }

    window.addEventListener('resize', resize);

    setup();
}
