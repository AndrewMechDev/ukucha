import { Router } from 'express';
import { handleNfcAuth } from '../../controllers/iot.controller';

const router = Router();

// Endpoint: POST /api/v1/iot/nfc-auth
router.post('/nfc-auth', handleNfcAuth);

export default router;
