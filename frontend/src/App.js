import { useState, useEffect } from 'react'
import './App.css'

function App() {
    const [a, setA] = useState("");
    const [b, setB] = useState("");
    const [resultado, setResultado] = useState(null);
    const [historial, setHistorial] = useState([]);

    const sumar = async () => {
        const res = await fetch(`http://localhost:8089/calculadora-fast-api/sum?a=${a}&b=${b}`);
        const data = await res.json();
        setResultado(data.result); // ✅ corregido
        obtenerHistorial();
    };

    const obtenerHistorial = async () => {
        const res = await fetch("http://localhost:8089/calculadora-fast-api/history");
        const data = await res.json();
        setHistorial(data.history); // ✅ corregido
    };

    useEffect(() => {
        (async () => {
            await obtenerHistorial();
        })();
    }, [resultado]);

    return (
        <div className="calculator-body">
            <h1>Calculadora</h1>
            <input
                type="number"
                value={a}
                onChange={(e) => setA(e.target.value)}
                placeholder="Número 1"
            />
            <input
                type="number"
                value={b}
                onChange={(e) => setB(e.target.value)}
                placeholder="Número 2"
            />
            <button onClick={sumar}>Sumar</button>
            {resultado !== null && <h2>Resultado: {resultado}</h2>}
            <h3>Historial:</h3>
            <ul>
                {historial.map((op, i) => (
                    <li key={i}>
                        {op.a} + {op.b} = {op.result} ({op.date})
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default App
