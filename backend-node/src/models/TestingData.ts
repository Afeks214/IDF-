import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { ExcelFile } from './ExcelFile';

@Entity('testing_data')
export class TestingData {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 10 })
  buildingId!: string;

  @Column({ type: 'varchar', length: 100 })
  buildingManager!: string;

  @Column({ type: 'varchar', length: 200, nullable: true })
  redTeam?: string;

  @Column({ type: 'varchar', length: 100 })
  inspectionType!: string;

  @Column({ type: 'varchar', length: 100 })
  inspectionLeader!: string;

  @Column({ type: 'int' })
  inspectionRound!: number;

  @Column({ type: 'varchar', length: 50, nullable: true })
  regulator1?: string;

  @Column({ type: 'varchar', length: 50, nullable: true })
  regulator2?: string;

  @Column({ type: 'date', nullable: true })
  executionSchedule?: Date;

  @Column({ type: 'date', nullable: true })
  targetCompletion?: Date;

  @Column({ type: 'boolean', default: false })
  coordinatedWithContractor!: boolean;

  @Column({ type: 'varchar', length: 500, nullable: true })
  defectReportAttached?: string;

  @Column({ type: 'boolean', default: false })
  reportDistributed!: boolean;

  @Column({ type: 'date', nullable: true })
  distributionDate?: Date;

  @ManyToOne(() => ExcelFile)
  @JoinColumn({ name: 'source_file_id' })
  sourceFile!: ExcelFile;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;
}