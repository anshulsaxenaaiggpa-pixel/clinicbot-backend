const { Client } = require('pg');

async function addTiming() {
    const client = new Client({
        connectionString: process.env.DATABASE_URL
    });
    
    await client.connect();
    
    const sql = `
        INSERT INTO clinic_timings (id, clinic_id, day_of_week, start_time, end_time, is_closed, lunch_enabled, lunch_start, lunch_end, created_at, updated_at) 
        VALUES 
        (gen_random_uuid(), 'aa4171cd-55b1-4da5-828e-00edcd67bbfd', 'monday', '09:00', '18:00', false, true, '13:00', '14:00', NOW(), NOW()),
        (gen_random_uuid(), 'aa4171cd-55b1-4da5-828e-00edcd67bbfd', 'saturday', '09:00', '14:00', false, false, NULL, NULL, NOW(), NOW()),
        (gen_random_uuid(), 'aa4171cd-55b1-4da5-828e-00edcd67bbfd', 'sunday', NULL, NULL, true, false, NULL, NULL, NOW(), NOW());
    `;
    
    await client.query(sql);
    console.log('✅ Clinic timing added successfully!');
    
    await client.end();
}

addTiming().catch(console.error);
