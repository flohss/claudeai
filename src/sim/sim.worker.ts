/// <reference lib="webworker" />
import type { Port } from './protocol';
import { SimulationServer } from './server';

new SimulationServer(self as unknown as Port).start();
