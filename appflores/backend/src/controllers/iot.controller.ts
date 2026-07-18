import { Request, Response } from 'express';
import { validateNfcTag } from '../services/nfc.service';

export const handleNfcAuth = async (req: Request, res: Response) => {
  try {
    const { encryptedPayload, signature } = req.body;

    if (!encryptedPayload || !signature) {
      return res.status(400).json({ error: 'Faltan credenciales del tag NFC' });
    }

    const validationResult = await validateNfcTag(encryptedPayload, signature);

    if (!validationResult.isValid) {
      return res.status(401).json({ error: 'Validación de firma NFC fallida.' });
    }

    const { specimenId } = validationResult;

    return res.status(200).json({
      success: true,
      message: 'Tag NFC validado con éxito',
      data: {
        specimenId,
        deepLink: `app://specimen/profile/${specimenId}`
      }
    });
  } catch (error) {
    console.error('[IoT Controller] Error en validación NFC:', error);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
};
