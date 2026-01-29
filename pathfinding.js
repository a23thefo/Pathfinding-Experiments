import {Cell, createCellGrid} from './pfclasses.js';
let grid = createCellGrid(rows, cols);
const rows = 25;
const cols = 40;
const cellSize = 30;
let pos;
const canvas = document.getElementById('pathfindingCanvas');
const ctx = canvas.getContext('2d');
console.log(grid);
function drawGrid(ctx) {
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            grid[r][c].draw(ctx);
        }
    }
}
drawGrid(ctx);

function click(event) {

}

// Thx to this guy https://dev.to/codepo8/quick-solution-getting-the-mouse-position-on-an-element-regardless-of-positioning-1pa2
const getPosition = event => {
    let x = event.clientX;
    let y = event.clientY;

    let pos = event.target.getBoundingClientRect();

    return {
        x: x - pos.x|1,
        y: y - pos.y|1
    };
}

canvas.addEventListener('click', click);
canvas.addEventListener('mousemove', event => {
    pos = getPosition(event);
    document.getElementById('currentMousePos').innerText = `X: ${pos.x}, Y: ${pos.y}`;
});