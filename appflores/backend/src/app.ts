import express from 'express';
import cors from 'cors';
import iotRoutes from './routes/v1/iot.routes';
// import { connectDatabase } from './config/database';

const app = express();

// Middlewares
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/v1/iot', iotRoutes);

// Database Connection
// connectDatabase();

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export default app;
